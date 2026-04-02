#!/usr/bin/env python3
# Advanced VN Proxy Scanner with Telegram Bot Control
# Production-ready - Scan ONLY Viettel & VN carriers IPs as proxies
# /scan [type] [speed] [quantity] - real-time append to classified files

import ssl
import json
import random
import re
import time
import sys
import socket
import struct
import string
import nest_asyncio
import asyncio
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse
from typing import Dict, List, Any
from dataclasses import dataclass, field, asdict
from queue import Queue
from threading import Thread, Lock, Event
import warnings
import ipaddress

warnings.filterwarnings('ignore')

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import telegram
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

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
    country: str = 'Unknown'
    region: str = 'Unknown'
    city: str = 'Unknown'
    isp: str = 'Unknown'
    timezone: str = 'Unknown'
    latitude: float = 0.0
    longitude: float = 0.0
    response_time: float = 0.0
    speed_category: str = 'unknown'
    anonymity: str = 'unknown'
    anonymity_score: int = 0
    reliability_score: float = 0.0
    success_count: int = 0
    fail_count: int = 0
    last_checked: float = 0.0
    protocols_supported: List[str] = field(default_factory=list)
    ssl_capabilities: Dict[str, Any] = field(default_factory=dict)
    bypass_capabilities: Dict[str, bool] = field(default_factory=dict)
    fingerprint: str = ''
    ja3_hash: str = ''
    http_version: str = '1.1'
    websocket_support: bool = False
    udp_support: bool = False
    dns_leak_risk: bool = False
    webrtc_leak_risk: bool = False
    real_ip_exposed: bool = False
    headers_leaked: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    def get_proxy_url(self):
        return f"{self.ptype}://{self.address}"

class StealthEngine:
    def __init__(self):
        self.tls_versions = [ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3]
        self.cipher_suites = [
            'ECDHE-ECDSA-AES128-GCM-SHA256',
            'ECDHE-RSA-AES128-GCM-SHA256',
            'ECDHE-ECDSA-AES256-GCM-SHA384',
            'ECDHE-RSA-AES256-GCM-SHA384',
            'ECDHE-ECDSA-CHACHA20-POLY1305',
            'ECDHE-RSA-CHACHA20-POLY1305'
        ]
        self.ja3_fingerprints = self._load_ja3_fingerprints()
        self.current_fingerprint = None

    def _load_ja3_fingerprints(self):
        return [
            "769,47-53-5-10-49161-49162-49171-49172-50-56-19-4,0-10-11,23-24-25,0",
            "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21,29-23-24-25,0",
            "771,49195-49199-49196-49200-52393-52392-49161-49171-49162-49172-156-157-47-53-10,65281-0-23-35-13-5-18-16-30032-11-10,29-23-24-25,0"
        ]

    def generate_ssl_context(self, tls_version=None):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers(':'.join(self.cipher_suites))
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        if tls_version:
            context.maximum_version = tls_version
        return context

    def rotate_ja3(self):
        self.current_fingerprint = random.choice(self.ja3_fingerprints)
        return self.current_fingerprint

    def generate_random_padding(self, min_size=100, max_size=1000):
        size = random.randint(min_size, max_size)
        return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

class RequestEngine:
    def __init__(self, stealth_engine, timeout=5):
        self.stealth = stealth_engine
        self.timeout = timeout
        self.session_pool = []
        self.max_sessions = 50
        self._init_session_pool()

    def _init_session_pool(self):
        for _ in range(self.max_sessions):
            session = urllib3.PoolManager(
                num_pools=10,
                maxsize=100,
                ssl_context=self.stealth.generate_ssl_context(),
                timeout=urllib3.Timeout(connect=2.0, read=self.timeout),
                retries=urllib3.Retry(total=0, redirect=2, raise_on_redirect=False, raise_on_status=False)
            )
            self.session_pool.append(session)

    def get_session(self):
        return random.choice(self.session_pool)

    def craft_stealth_headers(self, target_url, proxy_info=None):
        ua = self._select_user_agent()
        parsed = urlparse(target_url)
        headers = {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'en-CA,en;q=0.7']),
            'Accept-Encoding': random.choice(['gzip, deflate, br', 'gzip, deflate']),
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': random.choice(['max-age=0', 'no-cache', 'no-store']),
            'Referer': self._generate_referer(parsed.netloc),
            'X-Forwarded-For': self._generate_x_forwarded_for(proxy_info),
            'X-Real-IP': self._generate_random_ip(),
        }
        if random.random() > 0.5:
            headers['Sec-CH-UA'] = '"Chromium";v="' + str(random.randint(110, 130)) + '", "Not:A-Brand";v="99"'
            headers['Sec-CH-UA-Mobile'] = '?0'
            headers['Sec-CH-UA-Platform'] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
        return headers

    def _select_user_agent(self):
        uas = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0'
        ]
        return random.choice(uas)

    def _generate_referer(self, domain):
        referers = [
            'https://www.google.com/',
            'https://www.bing.com/',
            'https://duckduckgo.com/',
            'https://search.yahoo.com/',
            f"https://{domain}/",
            'https://www.facebook.com/',
            'https://twitter.com/'
        ]
        return random.choice(referers)

    def _generate_x_forwarded_for(self, proxy_info=None):
        if proxy_info:
            return proxy_info.address.split(':')[0]
        return self._generate_random_ip()

    def _generate_random_ip(self):
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    def execute_request(self, url, proxy_url=None, method='GET', data=None, extra_headers=None, allow_redirects=True):
        session = self.get_session()
        headers = self.craft_stealth_headers(url)
        if extra_headers:
            headers.update(extra_headers)
        try:
            if proxy_url:
                proxy_parts = urlparse(proxy_url)
                proxy_scheme = proxy_parts.scheme
                if proxy_scheme in ['http', 'https']:
                    proxy_manager = urllib3.ProxyManager(
                        proxy_url=proxy_url,
                        ssl_context=self.stealth.generate_ssl_context(),
                        timeout=urllib3.Timeout(connect=2.0, read=self.timeout)
                    )
                    response = proxy_manager.request(method, url, headers=headers, body=data, redirect=allow_redirects, preload_content=False)
                else:
                    response = session.request(method, url, headers=headers, body=data, redirect=allow_redirects, preload_content=False)
            else:
                response = session.request(method, url, headers=headers, body=data, redirect=allow_redirects, preload_content=False)
            body = response.read()
            response.release_conn()
            return {'status': response.status, 'headers': dict(response.headers), 'body': body, 'url': response.geturl(), 'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

class BypassValidator:
    def __init__(self, request_engine):
        self.req = request_engine
        self.bypass_targets = {
            'cloudflare': 'https://www.cloudflare.com/',
            'akamai': 'https://www.akamai.com/',
            'incapsula': 'https://www.imperva.com/',
            'datadome': 'https://datadome.co/',
            'perimeterx': 'https://www.perimeterx.com/',
            'fastly': 'https://www.fastly.com/'
        }
        self.captcha_sites = ['https://www.google.com/recaptcha/api2/demo']

    def test_bypass_capability(self, proxy_info):
        results = {}
        proxy_url = proxy_info.get_proxy_url()
        for name, url in self.bypass_targets.items():
            result = self._test_single_bypass(url, proxy_url, name)
            results[name] = result
        for site in self.captcha_sites:
            result = self._test_single_bypass(site, proxy_url, 'captcha')
            results[f"captcha_{urlparse(site).netloc}"] = result
        return results

    def _test_single_bypass(self, url, proxy_url, waf_name):
        try:
            start = time.time()
            response = self.req.execute_request(url, proxy_url=proxy_url)
            elapsed = time.time() - start
            if not response['success']:
                return {'success': False, 'time': elapsed, 'blocked': True}
            body = response['body'].decode('utf-8', errors='ignore').lower()
            blocked_indicators = ['cloudflare', 'captcha', 'challenge', 'blocked', 'access denied', 'forbidden', '403', 'bot detection']
            is_blocked = any(ind in body for ind in blocked_indicators) or response['status'] in [403, 406, 429, 503]
            return {'success': not is_blocked, 'time': elapsed, 'blocked': is_blocked, 'status': response['status']}
        except Exception as e:
            return {'success': False, 'error': str(e), 'blocked': True}

    def calculate_bypass_score(self, results):
        total = len(results)
        passed = sum(1 for r in results.values() if r.get('success', False))
        return (passed / total * 100) if total > 0 else 0

class AnonymityTester:
    def __init__(self, request_engine):
        self.req = request_engine
        self.leak_test_urls = ['http://httpbin.org/get', 'http://ip-api.com/json/', 'https://api.ipify.org?format=json']

    def comprehensive_anonymity_test(self, proxy_info):
        proxy_url = proxy_info.get_proxy_url()
        results = {'headers_leaked': [], 'ip_exposed': False, 'real_ip': None, 'anonymity_level': 'unknown', 'anonymity_score': 0}
        for url in self.leak_test_urls:
            try:
                response = self.req.execute_request(url, proxy_url=proxy_url)
                if response['success']:
                    self._analyze_response(response, results, proxy_info)
            except:
                continue
        results['anonymity_level'] = self._calculate_anonymity_level(results)
        results['anonymity_score'] = self._calculate_anonymity_score(results)
        return results

    def _analyze_response(self, response, results, proxy_info):
        try:
            body = response['body'].decode('utf-8', errors='ignore')
            headers = response['headers']
            leak_headers = ['x-forwarded-for', 'x-real-ip', 'x-client-ip', 'cf-connecting-ip']
            for header in leak_headers:
                if header in headers:
                    results['headers_leaked'].append(header)
                    if header in ['x-forwarded-for', 'x-real-ip']:
                        results['ip_exposed'] = True
                        results['real_ip'] = headers[header]
        except:
            pass

    def _calculate_anonymity_level(self, results):
        if results['ip_exposed'] or len(results['headers_leaked']) > 2:
            return 'transparent'
        elif len(results['headers_leaked']) > 0:
            return 'anonymous'
        else:
            return 'elite'

    def _calculate_anonymity_score(self, results):
        score = 100
        if results['ip_exposed']:
            score -= 50
        score -= len(results['headers_leaked']) * 5
        return max(0, score)

class GeoIPResolver:
    def __init__(self):
        self.cache = {}

    def resolve(self, ip_address):
        if ip_address in self.cache:
            return self.cache[ip_address]
        try:
            import requests
            resp = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            data = resp.json()
            result = {
                'country': data.get('country', 'Unknown'),
                'region': data.get('regionName', 'Unknown'),
                'city': data.get('city', 'Unknown'),
                'isp': data.get('isp', 'Unknown'),
                'timezone': data.get('timezone', 'Unknown'),
                'latitude': data.get('lat', 0.0),
                'longitude': data.get('lon', 0.0)
            }
            self.cache[ip_address] = result
            return result
        except:
            return {'country': 'Vietnam', 'region': 'Unknown', 'city': 'Unknown', 'isp': 'VN Carrier', 'timezone': 'Unknown', 'latitude': 0.0, 'longitude': 0.0}

class ProtocolTester:
    def __init__(self, request_engine):
        self.req = request_engine

    def test_all_protocols(self, proxy_info):
        results = {'http': False, 'https': False, 'socks4': False, 'socks5': False, 'connect': False}
        try:
            host, port = proxy_info.address.split(':')
            port = int(port)
            results['http'] = self._test_http_proxy(host, port)
            results['https'] = self._test_https_proxy(host, port)
            results['socks4'] = self._test_socks4(host, port)
            results['socks5'] = self._test_socks5(host, port)
            results['connect'] = self._test_connect_method(host, port)
        except:
            pass
        return results

    def _test_http_proxy(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            request = f"GET http://httpbin.org/ip HTTP/1.1\r\nHost: httpbin.org\r\n\r\n"
            sock.send(request.encode())
            response = sock.recv(4096)
            sock.close()
            return b"200" in response or b"HTTP/1.1" in response
        except:
            return False

    def _test_https_proxy(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            ssock = context.wrap_socket(sock, server_hostname='httpbin.org')
            request = "GET /ip HTTP/1.1\r\nHost: httpbin.org\r\n\r\n"
            ssock.send(request.encode())
            response = ssock.recv(4096)
            ssock.close()
            return b"200" in response
        except:
            return False

    def _test_socks4(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            target_ip = socket.inet_aton('142.250.80.46')
            target_port = struct.pack('>H', 80)
            request = b'\x04\x01' + target_port + target_ip + b'\x00'
            sock.send(request)
            response = sock.recv(8)
            sock.close()
            return response[0:1] == b'\x00' and response[1:2] == b'\x5a'
        except:
            return False

    def _test_socks5(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            sock.send(b'\x05\x01\x00')
            auth = sock.recv(2)
            if auth[0:1] != b'\x05':
                sock.close()
                return False
            target_ip = socket.inet_aton('142.250.80.46')
            request = b'\x05\x01\x00\x01' + target_ip + struct.pack('>H', 80)
            sock.send(request)
            response = sock.recv(10)
            sock.close()
            return response[0:1] == b'\x05' and response[1:2] == b'\x00'
        except:
            return False

    def _test_connect_method(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            request = f"CONNECT httpbin.org:443 HTTP/1.1\r\nHost: httpbin.org:443\r\n\r\n"
            sock.send(request.encode())
            response = sock.recv(4096)
            sock.close()
            return b"200" in response or b"Connection established" in response
        except:
            return False

class AdvancedProxyChecker:
    def __init__(self, config, exporter, type_filter=None, speed_filter=None):
        self.config = config
        self.exporter = exporter
        self.type_filter = type_filter
        self.speed_filter = speed_filter
        self.stealth = StealthEngine()
        self.request_engine = RequestEngine(self.stealth, timeout=config['timeout'])
        self.bypass_validator = BypassValidator(self.request_engine)
        self.anonymity_tester = AnonymityTester(self.request_engine)
        self.geo_resolver = GeoIPResolver()
        self.protocol_tester = ProtocolTester(self.request_engine)
        self.proxy_queue = Queue()
        self.lock = Lock()
        self.stop_event = Event()
        self.stats = {'total': 0, 'checked': 0, 'valid': 0, 'invalid': 0, 'by_country': defaultdict(int), 'by_type': defaultdict(int), 'by_speed': defaultdict(int), 'by_anonymity': defaultdict(int)}
        self.live_proxies = []
        self.classified_proxies = {'elite': [], 'anonymous': [], 'transparent': [], 'fast': [], 'medium': [], 'slow': [], 'bypass_master': [], 'stable': []}
        self.check_urls = ['http://httpbin.org/get', 'http://ip-api.com/json/', 'https://api.ipify.org?format=json']

    def check_single_proxy(self, proxy_data):
        address = proxy_data['address']
        ptype = proxy_data.get('type', 'http')
        if self.type_filter and ptype.lower() != self.type_filter.lower():
            with self.lock:
                self.stats['invalid'] += 1
            return None
        proxy_info = ProxyInfo(address=address, ptype=ptype)
        check_results = []
        for _ in range(self.config['check_times']):
            result = self._perform_check(proxy_info)
            if result:
                check_results.append(result)
            time.sleep(random.uniform(0.1, 0.5))
        if len(check_results) < self.config['check_times'] // 2:
            with self.lock:
                self.stats['invalid'] += 1
            return None
        avg_time = sum(r['time'] for r in check_results) / len(check_results)
        proxy_info.response_time = round(avg_time, 3)
        proxy_info.success_count = len(check_results)
        proxy_info.last_checked = time.time()
        if avg_time < 1.0:
            proxy_info.speed_category = 'fast'
        elif avg_time < 3.0:
            proxy_info.speed_category = 'medium'
        else:
            proxy_info.speed_category = 'slow'
        if self.speed_filter:
            if self.speed_filter == 'f' and proxy_info.speed_category != 'fast':
                with self.lock:
                    self.stats['invalid'] += 1
                return None
            if self.speed_filter == 't' and proxy_info.speed_category != 'medium':
                with self.lock:
                    self.stats['invalid'] += 1
                return None
            if self.speed_filter == 's' and proxy_info.speed_category != 'slow':
                with self.lock:
                    self.stats['invalid'] += 1
                return None
        geo_data = self.geo_resolver.resolve(address.split(':')[0])
        proxy_info.country = geo_data['country']
        proxy_info.region = geo_data['region']
        proxy_info.city = geo_data['city']
        proxy_info.isp = geo_data['isp']
        if proxy_info.country.lower() not in ['vietnam', 'vn', 'viet nam']:
            with self.lock:
                self.stats['invalid'] += 1
            return None
        anon_results = self.anonymity_tester.comprehensive_anonymity_test(proxy_info)
        proxy_info.anonymity = anon_results['anonymity_level']
        proxy_info.anonymity_score = anon_results['anonymity_score']
        proxy_info.headers_leaked = anon_results['headers_leaked']
        proxy_info.real_ip_exposed = anon_results['ip_exposed']
        bypass_results = self.bypass_validator.test_bypass_capability(proxy_info)
        proxy_info.bypass_capabilities = {k: v['success'] for k, v in bypass_results.items()}
        bypass_score = self.bypass_validator.calculate_bypass_score(bypass_results)
        protocol_results = self.protocol_tester.test_all_protocols(proxy_info)
        proxy_info.protocols_supported = [k for k, v in protocol_results.items() if v]
        proxy_info.reliability_score = self._calculate_reliability(proxy_info, bypass_score)
        with self.lock:
            self.stats['valid'] += 1
            self.stats['by_country'][proxy_info.country] += 1
            self.stats['by_type'][ptype] += 1
            self.stats['by_speed'][proxy_info.speed_category] += 1
            self.stats['by_anonymity'][proxy_info.anonymity] += 1
            self.live_proxies.append(proxy_info)
            self.classified_proxies[proxy_info.anonymity].append(proxy_info)
            self.classified_proxies[proxy_info.speed_category].append(proxy_info)
            if bypass_score > 70:
                self.classified_proxies['bypass_master'].append(proxy_info)
            if proxy_info.reliability_score > 80:
                self.classified_proxies['stable'].append(proxy_info)
            self.exporter.append_proxy(proxy_info)
        return proxy_info

    def _perform_check(self, proxy_info):
        try:
            url = random.choice(self.check_urls)
            proxy_url = proxy_info.get_proxy_url()
            start = time.time()
            response = self.request_engine.execute_request(url, proxy_url=proxy_url)
            elapsed = time.time() - start
            if response['success'] and response['status'] == 200:
                return {'time': elapsed, 'status': response['status']}
            return None
        except:
            return None

    def _calculate_reliability(self, proxy_info, bypass_score):
        reliability = min(proxy_info.anonymity_score, 50) + bypass_score * 0.3 + (proxy_info.success_count / self.config['check_times']) * 20
        if proxy_info.speed_category == 'fast':
            reliability += 10
        elif proxy_info.speed_category == 'medium':
            reliability += 5
        return min(100, reliability)

    def worker_thread(self):
        while not self.stop_event.is_set():
            try:
                proxy_data = self.proxy_queue.get(timeout=1)
                if proxy_data is None:
                    break
                self.check_single_proxy(proxy_data)
                with self.lock:
                    self.stats['checked'] += 1
                self.proxy_queue.task_done()
            except:
                break

    def run(self, proxy_list):
        self.stats['total'] = len(proxy_list)
        self.live_proxies.clear()
        for cat in self.classified_proxies:
            self.classified_proxies[cat].clear()
        for proxy in proxy_list:
            self.proxy_queue.put(proxy)
        threads = []
        for _ in range(self.config['threads']):
            t = Thread(target=self.worker_thread)
            t.daemon = True
            t.start()
            threads.append(t)
        while self.stats['checked'] < self.stats['total'] and not self.stop_event.is_set():
            time.sleep(0.5)
        self.stop_event.set()
        for _ in range(self.config['threads']):
            self.proxy_queue.put(None)
        for t in threads:
            t.join(timeout=5)
        return self.live_proxies

class VNIPGenerator:
    def __init__(self):
        self.vn_cidrs = [
            "103.77.0.0/18", "171.224.0.0/11", "14.160.0.0/12", "27.64.0.0/12", "103.199.0.0/18",
            "113.160.0.0/11", "117.0.0.0/12", "118.69.0.0/16", "210.245.0.0/16", "123.16.0.0/13",
            "45.117.80.0/22", "103.232.120.0/22", "103.74.116.0/22", "171.232.0.0/13", "14.177.0.0/16",
            "113.161.0.0/16", "117.1.0.0/16", "118.70.0.0/16", "210.245.0.0/16", "123.17.0.0/16",
            "103.78.0.0/18", "171.225.0.0/16", "14.161.0.0/16", "27.65.0.0/16", "103.200.0.0/18",
            "113.162.0.0/16", "117.2.0.0/16", "118.71.0.0/16", "210.246.0.0/16", "123.18.0.0/16",
            "45.117.84.0/22", "103.232.124.0/22", "103.74.120.0/22", "171.233.0.0/16", "14.178.0.0/16",
            "113.163.0.0/16", "117.3.0.0/16", "118.72.0.0/16", "210.247.0.0/16", "123.19.0.0/16",
            "45.117.88.0/22", "103.232.128.0/22", "103.74.124.0/22", "171.234.0.0/16", "14.179.0.0/16",
            "113.164.0.0/16", "117.4.0.0/16", "118.73.0.0/16", "210.248.0.0/16", "123.20.0.0/16"
        ]

    def _get_default_port(self, ptype):
        ports = {
            'http': random.choice([80, 8080, 3128, 8888, 8081]),
            'https': random.choice([443, 8443, 8080]),
            'socks4': random.choice([1080, 1081, 9050, 4153]),
            'socks5': random.choice([1080, 1081, 9050, 9150, 1085])
        }
        return ports.get(ptype.lower(), 8080)

    def generate(self, num_proxies=5000, ptype='http'):
        proxies = []
        used = set()
        while len(proxies) < num_proxies:
            cidr = random.choice(self.vn_cidrs)
            try:
                net = ipaddress.ip_network(cidr)
                ip_int = random.randint(int(net.network_address) + 1, int(net.broadcast_address) - 1)
                ip_str = str(ipaddress.ip_address(ip_int))
                if ip_str in used:
                    continue
                used.add(ip_str)
                port = self._get_default_port(ptype)
                proxies.append({'address': f"{ip_str}:{port}", 'type': ptype})
            except:
                continue
        random.shuffle(proxies)
        return proxies

class ProxyFetcher:
    def __init__(self, stealth_engine):
        self.stealth = stealth_engine
        self.req = RequestEngine(stealth_engine)
        self.vn_generator = VNIPGenerator()

    def load_sources(self, filepath='nguon.json'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                sources = json.load(f)
            print(f"{C.G}[NGUON]{C.N} Loaded {len(sources)} sources from nguon.json (ignored for VN IP scan)")
            return sources
        except:
            print(f"{C.Y}[NGUON]{C.N} nguon.json not found or invalid - using Viettel & VN carriers IP ranges")
            return []

    def fetch_all(self, proxy_type='http', quantity=5000):
        print(f"{C.C}[VN-IP]{C.N} Generating {quantity * 3} IPs from Viettel, VNPT, FPT, Mobifone ranges...")
        all_proxies = self.vn_generator.generate(quantity * 3, proxy_type)
        print(f"{C.G}[VN-IP]{C.N} Generated {len(all_proxies)} VN carrier IPs ready for scan")
        return all_proxies

class ProxyDeduplicator:
    @staticmethod
    def deduplicate(proxy_list):
        seen = set()
        unique = []
        for p in proxy_list:
            key = f"{p['address']}:{p['type']}"
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique

    @staticmethod
    def batch(proxy_list, batch_size):
        return proxy_list[:batch_size]

class ResultExporter:
    def __init__(self, output_dir='results'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.live_file = self.output_dir / f"vn_live_{self.timestamp}.txt"

    def append_proxy(self, proxy_info):
        """Real-time append every valid proxy to classified files"""
        # Live file
        with open(self.live_file, 'a', encoding='utf-8') as f:
            f.write(f"{proxy_info.address}|{proxy_info.ptype}|{proxy_info.speed_category}|{proxy_info.anonymity}|{proxy_info.reliability_score:.1f}\n")
        # Speed + type file
        speed_file = self.output_dir / f"vn_{proxy_info.speed_category}_{proxy_info.ptype}_{self.timestamp}.txt"
        with open(speed_file, 'a', encoding='utf-8') as f:
            f.write(f"{proxy_info.address}\n")
        # Anonymity file
        anon_file = self.output_dir / f"vn_{proxy_info.anonymity}_{self.timestamp}.txt"
        with open(anon_file, 'a', encoding='utf-8') as f:
            f.write(f"{proxy_info.address}\n")

    def export_final(self, proxy_infos, classified):
        self._export_txt(proxy_infos, f'vn_live_final_{self.timestamp}.txt')
        self._export_json(proxy_infos, f'vn_detailed_{self.timestamp}.json')
        self._export_csv(proxy_infos, f'vn_report_{self.timestamp}.csv')
        for category, proxies in classified.items():
            if proxies:
                self._export_simple(proxies, f'vn_{category}_{self.timestamp}.txt')

    def _export_txt(self, proxy_infos, filename):
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            for p in proxy_infos:
                f.write(f"{p.address}|{p.ptype}|{p.country}|{p.response_time}s|{p.speed_category}|{p.anonymity}|{p.reliability_score:.1f}\n")

    def _export_json(self, proxy_infos, filename):
        filepath = self.output_dir / filename
        data = [p.to_dict() for p in proxy_infos]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _export_csv(self, proxy_infos, filename):
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("address,type,country,region,city,isp,response_time,speed,anonymity,anonymity_score,reliability_score,protocols_supported\n")
            for p in proxy_infos:
                protocols = ';'.join(p.protocols_supported)
                f.write(f"{p.address},{p.ptype},{p.country},{p.region},{p.city},{p.isp},{p.response_time},{p.speed_category},{p.anonymity},{p.anonymity_score},{p.reliability_score:.1f},{protocols}\n")

    def _export_simple(self, proxy_infos, filename):
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            for p in proxy_infos:
                f.write(f"{p.address}\n")

class TelegramBotController:
    def __init__(self, token, allowed_users=None):
        self.token = token
        self.allowed_users = allowed_users or []
        self.application = None
        self.scanner = None
        self.fetcher = None
        self.exporter = None
        self.config = {'threads': 50, 'timeout': 10, 'check_times': 3, 'batch': 5000}
        self.current_scan_task = None
        self.is_scanning = False

    async def start(self):
        self.application = Application.builder().token(self.token).build()
        commands = [
            BotCommand("start", "Khởi động bot"),
            BotCommand("st", "Cài đặt cấu hình"),
            BotCommand("scan", "Quét proxy VN - /scan [type] [f/t/s] [số lượng]"),
            BotCommand("stop", "Dừng quét"),
            BotCommand("status", "Trạng thái"),
            BotCommand("config", "Xem cấu hình"),
            BotCommand("help", "Trợ giúp")
        ]
        await self.application.bot.set_my_commands(commands)
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("st", self.cmd_settings))
        self.application.add_handler(CommandHandler("scan", self.cmd_scan))
        self.application.add_handler(CommandHandler("stop", self.cmd_stop))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("config", self.cmd_config))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        print(f"{C.G}[TELEGRAM]{C.N} Bot started successfully.")

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.allowed_users and update.effective_user.id not in self.allowed_users:
            await update.message.reply_text("Bạn không có quyền.")
            return
        await update.message.reply_text("Fuck .\nDùng /help để xem lệnh.")

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.allowed_users and update.effective_user.id not in self.allowed_users:
            await update.message.reply_text("Bạn không có quyền.")
            return
        if not context.args:
            await update.message.reply_text(
                "Cách dùng:\n"
                "/st threads <số>\n"
                "/st timeout <giây>\n"
                "/st check_times <số>\n"
                "/st batch <số>\n\n"
                "Ví dụ: /st threads 100 timeout 8"
            )
            return
        args = context.args
        i = 0
        while i < len(args):
            key = args[i]
            if i+1 < len(args):
                val = args[i+1]
                if key == 'threads':
                    self.config['threads'] = int(val)
                elif key == 'timeout':
                    self.config['timeout'] = int(val)
                elif key == 'check_times':
                    self.config['check_times'] = int(val)
                elif key == 'batch':
                    self.config['batch'] = int(val)
                i += 2
            else:
                i += 1
        await update.message.reply_text(f"Cấu hình mới:\n{json.dumps(self.config, indent=2)}")

    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"Cấu hình hiện tại:\n{json.dumps(self.config, indent=2)}")

    async def cmd_scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.allowed_users and update.effective_user.id not in self.allowed_users:
            await update.message.reply_text("Bạn không có quyền.")
            return
        if self.is_scanning:
            await update.message.reply_text("Đang quét. Dùng /stop để dừng.")
            return

        args = context.args
        proxy_type = 'http'
        speed_filter = None
        quantity = self.config['batch']

        if args:
            proxy_type = args[0].lower()
            if proxy_type in ['sock5', 'socks5']:
                proxy_type = 'socks5'
            elif proxy_type in ['sock4', 'socks4']:
                proxy_type = 'socks4'
            if len(args) > 1:
                if args[1].lower() in ['f', 't', 's']:
                    speed_filter = args[1].lower()
                else:
                    try:
                        quantity = int(args[1])
                    except:
                        pass
            if len(args) > 2:
                try:
                    quantity = int(args[2])
                except:
                    pass

        await update.message.reply_text(f"Bắt đầu quét {quantity} proxy VN loại {proxy_type.upper()} - Tốc độ: {speed_filter or 'tất cả'} từ Viettel & các nhà mạng VN...")

        self.is_scanning = True
        self.current_scan_task = asyncio.create_task(self.start_scan(update, proxy_type, speed_filter, quantity))

    async def start_scan(self, update, proxy_type, speed_filter, quantity):
        try:
            stealth = StealthEngine()
            self.fetcher = ProxyFetcher(stealth)
            self.fetcher.load_sources('nguon.json')
            self.exporter = ResultExporter()

            all_proxies = self.fetcher.fetch_all(proxy_type, quantity)
            dedup = ProxyDeduplicator()
            unique_proxies = dedup.deduplicate(all_proxies)
            batched = dedup.batch(unique_proxies, quantity * 2)

            await update.message.reply_text(f"Đã sinh {len(batched)} IP Viettel/VN carriers. Bắt đầu kiểm tra...")

            checker = AdvancedProxyChecker(self.config, self.exporter, type_filter=proxy_type, speed_filter=speed_filter)
            self.scanner = checker

            live_proxies = checker.run(batched)

            self.exporter.export_final(live_proxies, checker.classified_proxies)

            summary = (
                f" Scan hoàn tất!\n"
                f"Checked: {checker.stats['checked']}\n"
                f"Valid VN proxies: {checker.stats['valid']}\n"
                f"Fast: {len(checker.classified_proxies['fast'])}\n"
                f"Elite: {len(checker.classified_proxies['elite'])}\n"
                f"Files đã ghi real-time vào results/"
            )
            await update.message.reply_text(summary)

        except Exception as e:
            await update.message.reply_text(f"Lỗi: {str(e)}")
        finally:
            self.is_scanning = False
            self.current_scan_task = None

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.is_scanning and self.scanner:
            self.scanner.stop_event.set()
            await update.message.reply_text("Đã gửi lệnh dừng.")
        else:
            await update.message.reply_text("Không có scan đang chạy.")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.scanner:
            await update.message.reply_text("Chưa có scan nào.")
            return
        status = (
            f"Trạng thái:\n"
            f"Checked: {self.scanner.stats['checked']}/{self.scanner.stats['total']}\n"
            f"Valid VN: {self.scanner.stats['valid']}\n"
            f"Scanning: {self.is_scanning}"
        )
        await update.message.reply_text(status)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "Lệnh:\n"
            "/scan socks5 f 1000  → quét 1000 proxy socks5 tốc độ nhanh\n"
            "/scan http t 500     → quét 500 proxy http tốc độ trung bình\n"
            "/scan socks4 s 2000  → quét 2000 proxy socks4 tốc độ chậm\n"
            "/scan all f 3000     → quét tất cả loại, chỉ fast\n"
            "/st ...              → cài đặt threads, timeout...\n"
            "Mọi proxy valid được ghi NGAY lập tức vào file phân loại trong results/"
        )
        await update.message.reply_text(help_text)

def print_banner():
    banner = f"""{C.C}{C.BOLD}
Fuck U MOM haha 
{C.N}"""
    print(banner)
    print(f"{C.G}[MODE]{C.N} Scan proxy từ IP Viettel + VN carriers (không dùng list free)")

async def main():
    print_banner()

    TELEGRAM_TOKEN = "8532814614:AAG4GHtmBCvfZCl6rOCCkh8nqM3I6E8sKoM"
    ALLOWED_USERS = [6142661532]  

    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print(f"{C.R}ERROR: Thay token bot Telegram vào dòng TELEGRAM_TOKEN!{C.N}")
        sys.exit(1)

    bot = TelegramBotController(TELEGRAM_TOKEN, ALLOWED_USERS)
    await bot.start()
    print(f"{C.G}[SYSTEM]{C.N} Bot đang chạy - Nhấn Ctrl+C để dừng")
    await bot.application.run_polling()

if __name__ == '__main__':
    nest_asyncio.apply()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{C.Y}[SYSTEM]{C.N} Bot đã dừng.")
    except Exception as e:
        print(f"{C.R}[ERROR]{C.N} {str(e)}")
