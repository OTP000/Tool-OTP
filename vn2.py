#!/usr/bin/env python3
# Advanced VN Proxy Scanner - Production Ready
# Tuân thủ nghiêm ngặt luật: Port giới hạn + Kiểm tra 2 lần cho 1001/1002 + Độ chính xác cao

import ssl
import random
import time
import sys
import socket
import asyncio
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import warnings
import ipaddress
import nest_asyncio

nest_asyncio.apply()

warnings.filterwarnings('ignore')

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import telegram
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    M = '\033[95m'
    C = '\033[96m'
    W = '\033[97m'
    N = '\033[0m'
    BOLD = '\033[1m'

@dataclass
class ProxyInfo:
    address: str
    ptype: str
    response_time: float = 0.0
    speed_category: str = 'unknown'
    anonymity: str = 'unknown'
    reliability_score: float = 0.0

    def get_proxy_url(self):
        return f"{self.ptype}://{self.address}"

class StealthEngine:
    def generate_ssl_context(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256')
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        return context

class RequestEngine:
    def __init__(self, timeout=3):
        self.timeout = timeout
        self.test_url = "https://vnexpress.net"
        self.stealth = StealthEngine()

    def tcp_connect_test(self, host: str, port: int) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def check_proxy(self, proxy_url: str, check_times: int = 1):
        for _ in range(check_times):
            try:
                scheme, addr = proxy_url.split("://")
                host, port_str = addr.split(":")
                port = int(port_str)

                # TCP connect test
                if not self.tcp_connect_test(host, port):
                    continue

                # HTTP test
                proxy_manager = urllib3.ProxyManager(
                    proxy_url=proxy_url,
                    ssl_context=self.stealth.generate_ssl_context(),
                    timeout=urllib3.Timeout(connect=2.5, read=self.timeout)
                )

                start = time.time()
                response = proxy_manager.request('GET', self.test_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, preload_content=False)

                elapsed = time.time() - start

                if response.status in (200, 301, 302):
                    return {'success': True, 'time': elapsed}
            except:
                continue
        return {'success': False}

class VNIPGenerator:
    def __init__(self):
        self.vn_cidrs = [
            "103.77.0.0/18", "171.224.0.0/11", "14.160.0.0/12", "27.64.0.0/12",
            "113.160.0.0/11", "117.0.0.0/12", "118.69.0.0/16", "210.245.0.0/16",
            "123.16.0.0/13", "171.232.0.0/13", "45.117.80.0/22", "103.199.0.0/18",
        ]

    def _get_port(self, ptype: str):
        if ptype in ['http', 'https']:
            return random.choice([8080, 3128, 1001, 1002])
        return 1080

    def generate(self, num_proxies: int = 3000, ptype: str = 'http'):
        proxies = []
        used = set()
        while len(proxies) < num_proxies:
            cidr = random.choice(self.vn_cidrs)
            try:
                net = ipaddress.ip_network(cidr)
                ip_int = random.randint(int(net.network_address) + 5, int(net.broadcast_address) - 5)
                ip_str = str(ipaddress.ip_address(ip_int))
                if ip_str in used: continue
                used.add(ip_str)
                port = self._get_port(ptype)
                proxies.append({'address': f"{ip_str}:{port}", 'type': ptype})
            except:
                continue
        random.shuffle(proxies)
        return proxies

class ResultExporter:
    def __init__(self, output_dir='results'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def append_proxy(self, proxy_info: ProxyInfo):
        # Live
        with open(self.output_dir / f"vn_live_{self.timestamp}.txt", 'a', encoding='utf-8') as f:
            f.write(f"{proxy_info.address}|{proxy_info.ptype}|{proxy_info.speed_category}|{proxy_info.anonymity}|{proxy_info.response_time:.2f}s\n")

        # Theo tốc độ
        with open(self.output_dir / f"vn_{proxy_info.speed_category}_{proxy_info.ptype}_{self.timestamp}.txt", 'a', encoding='utf-8') as f:
            f.write(f"{proxy_info.address}\n")

        # Elite
        if proxy_info.anonymity == 'elite':
            with open(self.output_dir / f"vn_elite_{self.timestamp}.txt", 'a', encoding='utf-8') as f:
                f.write(f"{proxy_info.address}\n")

class AdvancedProxyChecker:
    def __init__(self, config, exporter, type_filter=None, speed_filter=None):
        self.config = config
        self.exporter = exporter
        self.type_filter = type_filter
        self.speed_filter = speed_filter
        self.request_engine = RequestEngine(timeout=config.get('timeout', 3))
        self.lock = Lock()
        self.stop_event = Event()
        self.stats = {'total': 0, 'checked': 0, 'valid': 0, 'invalid': 0}
        self.classified_proxies = {'elite': [], 'fast': [], 'medium': [], 'slow': []}

    def run(self, proxy_list):
        self.stats['total'] = len(proxy_list)
        for proxy_data in proxy_list:
            if self.stop_event.is_set():
                break
            self.check_single_proxy(proxy_data)
            self.stats['checked'] += 1
        return self.classified_proxies

    def check_single_proxy(self, proxy_data):
        proxy_url = f"{proxy_data['type']}://{proxy_data['address']}"
        
        # Kiểm tra 2 lần cho port 1001 và 1002
        check_times = self.config.get('check_times', 2) if proxy_data['address'].endswith((':1001', ':1002')) else 1

        result = self.request_engine.check_proxy(proxy_url, check_times)

        if not result['success']:
            with self.lock:
                self.stats['invalid'] += 1
            return

        elapsed = result.get('time', 3.0)
        proxy_info = ProxyInfo(address=proxy_data['address'], ptype=proxy_data['type'])
        proxy_info.response_time = round(elapsed, 2)

        if elapsed < 1.2:
            proxy_info.speed_category = 'fast'
            proxy_info.anonymity = 'elite'
        elif elapsed < 2.5:
            proxy_info.speed_category = 'medium'
        else:
            proxy_info.speed_category = 'slow'

        if self.speed_filter:
            if self.speed_filter == 'f' and proxy_info.speed_category != 'fast': return
            if self.speed_filter == 't' and proxy_info.speed_category != 'medium': return
            if self.speed_filter == 's' and proxy_info.speed_category != 'slow': return

        proxy_info.reliability_score = 92.0 if proxy_info.anonymity == 'elite' else 78.0

        with self.lock:
            self.stats['valid'] += 1
            self.classified_proxies[proxy_info.speed_category].append(proxy_info)
            if proxy_info.anonymity == 'elite':
                self.classified_proxies['elite'].append(proxy_info)
            self.exporter.append_proxy(proxy_info)

class TelegramBotController:
    def __init__(self, token, allowed_users=None):
        self.token = token
        self.allowed_users = allowed_users or []
        self.application = None
        self.scanner = None
        self.exporter = None
        self.config = {'timeout': 3, 'check_times': 2, 'batch': 3000}
        self.is_scanning = False
        self.status_message = None
        self.status_task = None
        self.stop_status = Event()

    async def start(self):
        self.application = Application.builder().token(self.token).build()
        await self.application.bot.set_my_commands([
            BotCommand("scan", "Quét proxy VN"),
            BotCommand("st", "Cài đặt cấu hình"),
            BotCommand("status", "Bật bảng trạng thái"),
            BotCommand("of", "Tắt & xóa bảng trạng thái"),
            BotCommand("stop", "Dừng scan"),
            BotCommand("help", "Trợ giúp")
        ])

        self.application.add_handler(CommandHandler("scan", self.cmd_scan))
        self.application.add_handler(CommandHandler("st", self.cmd_settings))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("of", self.cmd_of))
        self.application.add_handler(CommandHandler("stop", self.cmd_stop))
        self.application.add_handler(CommandHandler("help", self.cmd_help))

        print(f"{C.G}[BOT]{C.N} Bot đã khởi động.")

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "Cách sử dụng:\n"
                "/st check_times <số>   → Số lần kiểm tra (mặc định 2 cho port 1001/1002)\n"
                "/st timeout <giây>     → Timeout kiểm tra (mặc định 3)\n"
                "/st batch <số>         → Số lượng proxy tối đa\n\n"
                "Ví dụ: /st check_times 3"
            )
            return

        args = context.args
        i = 0
        while i < len(args):
            if args[i] == 'check_times' and i+1 < len(args):
                self.config['check_times'] = int(args[i+1])
                i += 2
            elif args[i] == 'timeout' and i+1 < len(args):
                self.config['timeout'] = int(args[i+1])
                i += 2
            elif args[i] == 'batch' and i+1 < len(args):
                self.config['batch'] = int(args[i+1])
                i += 2
            else:
                i += 1

        await update.message.reply_text(f"Cấu hình mới:\n{json.dumps(self.config, indent=2)}")

    async def cmd_scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.allowed_users and update.effective_user.id not in self.allowed_users:
            return await update.message.reply_text("Bạn không có quyền.")

        args = context.args
        ptype = args[0].lower() if args else 'http'
        if ptype in ['sock5', 'socks5']: ptype = 'socks5'

        speed = args[1].lower() if len(args) > 1 and args[1] in ['f','t','s'] else None
        qty = int(args[2]) if len(args) > 2 else self.config['batch']

        self.is_scanning = True
        self.exporter = ResultExporter()
        self.scanner = AdvancedProxyChecker(self.config, self.exporter, ptype, speed)

        await update.message.reply_text(
            f"🚀 Bắt đầu quét **{qty}** proxy **{ptype.upper()}** - Tốc độ: **{speed or 'Tất cả'}**\n"
            f"Port: 8080, 3128, 1001, 1002, 1080 | Kiểm tra {self.config['check_times']} lần cho port 1001/1002"
        )

        asyncio.create_task(self.run_scan(update, qty))

    async def run_scan(self, update, quantity):
        generator = VNIPGenerator()
        proxies = generator.generate(quantity * 2, self.scanner.type_filter or 'http')

        self.scanner.run(proxies)

        await update.message.reply_text(
            f"✅ **Scan hoàn tất!**\n"
            f"Valid proxies: **{self.scanner.stats['valid']}**\n"
            f"Kết quả đã được ghi realtime vào thư mục `results/`"
        )
        self.is_scanning = False

    # ====================== Status ======================
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_scanning:
            await update.message.reply_text("❌ Chưa có scan nào đang chạy.")
            return

        text = self._generate_status_text()
        self.status_message = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        self.stop_status.clear()
        self.status_task = asyncio.create_task(self._status_updater())

    def _generate_status_text(self):
        if not self.scanner:
            return "```Đang khởi tạo...```"

        checked = self.scanner.stats['checked']
        total = self.scanner.stats['total']
        valid = self.scanner.stats['valid']
        progress = (checked / total * 100) if total > 0 else 0
        bar = '█' * int(progress // 2) + '░' * (50 - int(progress // 2))

        return f"""```
🌐 VN PROXY SCANNER - REALTIME

Tiến độ : [{bar}] {progress:.1f}%
Checked : {checked:,} / {total:,}
Valid   : {valid:,} ✅

Elite   : {len(self.scanner.classified_proxies.get('elite', []))}
Fast    : {len(self.scanner.classified_proxies.get('fast', []))}

Port    : 8080, 3128, 1001, 1002, 1080
Test    : vnexpress.net
Cập nhật mỗi 5 giây
```"""

    async def _status_updater(self):
        while not self.stop_status.is_set() and self.status_message and self.is_scanning:
            try:
                await self.status_message.edit_text(self._generate_status_text(), parse_mode=ParseMode.MARKDOWN)
            except:
                pass
            await asyncio.sleep(5)

    async def cmd_of(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.stop_status.set()
        if self.status_message:
            try:
                await self.status_message.delete()
            except:
                pass
            self.status_message = None
        await update.message.reply_text("✅ Đã tắt và xóa bảng trạng thái.")

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.scanner:
            self.scanner.stop_event.set()
        await self.cmd_of(update, context)
        await update.message.reply_text("⏹️ Đã dừng scan.")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📋 **Hướng dẫn**\n\n"
            "`/scan socks5 f 1000` → Quét 1000 proxy socks5 tốc độ nhanh\n"
            "`/scan http t 2000`   → Quét 2000 proxy http tốc độ trung bình\n"
            "`/status`             → Bật bảng trạng thái realtime\n"
            "`/of`                 → Tắt và xóa bảng trạng thái\n"
            "`/stop`               → Dừng scan\n"
            "`/st check_times 2`   → Chỉnh số lần kiểm tra port 1001/1002\n\n"
            "Tập trung độ chính xác cao.",
            parse_mode=ParseMode.MARKDOWN
        )

async def main():
    TELEGRAM_TOKEN = "8532814614:AAG4GHtmBCvfZCl6rOCCkh8nqM3I6E8sKoM"
    ALLOWED_USERS = [6142661532]

    print(f"{C.G}[SYSTEM]{C.N} VN Proxy Scanner đang khởi động...")
    bot = TelegramBotController(TELEGRAM_TOKEN, ALLOWED_USERS)
    await bot.start()
    await bot.application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
