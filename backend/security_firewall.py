import re
import time
from collections import defaultdict
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime

# ==============================================================================
# LỚP 1: BẪY HONEYPOT & DANH SÁCH BOT / SCANNER LỖ HỔNG QUỐC TẾ
# ==============================================================================
HONEYPOT_PATHS = {
    "/wp-admin", "/wp-login.php", "/phpmyadmin", "/pma", "/.env", "/.git",
    "/.git/config", "/config.json", "/xmlrpc.php", "/actuator", "/actuator/health",
    "/swagger-ui.html", "/shell.php", "/admin.php", "/setup.php", "/debug",
    "/.aws/credentials", "/web.config", "/.svn", "/backup.sql", "/dump.sql",
    "/id_rsa", "/eval-stdin.php", "/vendor/.env", "/storage/.env"
}

BLOCKED_USER_AGENTS = [
    "sqlmap", "nikto", "dirbuster", "masscan", "zgrab", "gobuster",
    "wprecon", "nmap", "acunetix", "havij", "metasploit", "censys",
    "shodan", "projectdiscovery", "nuclei", "httpx", "ffuf", "wpscan",
    "openvas", "nessus", "qualys", "dirb", "hydra", "medusa", "burpcollaborator"
]

# ==============================================================================
# LỚP 3: MẪU TẤN CÔNG OWASP TOP 10 (SQLi, XSS, RCE, Path Traversal, SSRF)
# ==============================================================================
MALICIOUS_PATTERNS = [
    # 1. SQL Injection (Union, Blind, Stacked, Comment Injection, Time-based)
    re.compile(r"(\bunion\b.*\bselect\b|\bselect\b.*\bfrom\b|\binsert\b.*\binto\b|\bdelete\b.*\bfrom\b|\bdrop\b\s+(table|database))", re.IGNORECASE),
    re.compile(r"(--|#|/\*|\*/|;\s*waitfor\b|\bor\b\s+1\s*=\s*1\b|\band\b\s+1\s*=\s*1\b)", re.IGNORECASE),
    re.compile(r"(\bexec\s+sp_|\bxp_cmdshell\b|\bsp_executesql\b|\bpg_sleep\b|\bsleep\(\d+\)|\bbenchmark\(\d+,)", re.IGNORECASE),
    
    # 2. Path Traversal & LFI/RFI
    re.compile(r"(\.\./|\.\.\\|/etc/passwd|/etc/shadow|/proc/self|/windows/win\.ini|\bboot\.ini\b)", re.IGNORECASE),
    
    # 3. Cross-Site Scripting (XSS & HTML Injection)
    re.compile(r"(<script\b|javascript:|onerror\s*=|onload\s*=|alert\(|<iframe\b|<object\b|<embed\b|vbscript:|data:text/html)", re.IGNORECASE),
    
    # 4. Remote Code Execution (RCE & Command Injection)
    re.compile(r"(/bin/sh|/bin/bash|cmd\.exe|powershell|wget\s+|curl\s+http|\bwhoami\b|\bcat\s+/etc/|\bsystem\(|\bpassthru\()", re.IGNORECASE),

    # 5. Server-Side Request Forgery (SSRF)
    re.compile(r"(169\.254\.169\.254|metadata\.google\.internal)", re.IGNORECASE)
]

class SecurityFirewallManager:
    """Hệ thống Quản Trị Tường Lửa 7 Lớp Chuẩn Enterprise Shield v5.0"""
    def __init__(self):
        self.request_history = defaultdict(list)
        self.auth_request_history = defaultdict(list)
        self.failed_logins = defaultdict(list)
        self.blocked_ips = {}
        self.audit_logs = []
        
        # Thống kê phân loại tấn công (SIEM Metrics)
        self.metrics = {
            "total_threats_blocked": 0,
            "sqli_blocked": 0,
            "xss_blocked": 0,
            "rce_blocked": 0,
            "scanners_blocked": 0,
            "honeypot_trapped": 0,
            "ddos_rate_limited": 0,
            "bruteforce_blocked": 0
        }

    def get_client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "127.0.0.1"

    def is_ip_blocked(self, ip: str) -> bool:
        now = time.time()
        if ip in self.blocked_ips:
            if now < self.blocked_ips[ip]:
                return True
            else:
                del self.blocked_ips[ip]
        return False

    def block_ip(self, ip: str, duration_seconds: int = 900, reason: str = "Tấn công độc hại", category: str = "general"):
        self.blocked_ips[ip] = time.time() + duration_seconds
        self.log_event(ip, "IP_BLOCKED", f"Khóa IP {duration_seconds//60} phút. Lý do: {reason}", is_threat=True, category=category)
        if category in self.metrics:
            self.metrics[category] += 1

    def unblock_ip(self, ip: str):
        if ip in self.blocked_ips:
            del self.blocked_ips[ip]
        if ip in self.failed_logins:
            del self.failed_logins[ip]

    def log_event(self, ip: str, event_type: str, details: str, is_threat: bool = False, category: str = "info"):
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
            "ip": ip,
            "event_type": event_type,
            "details": details,
            "is_threat": is_threat,
            "category": category
        }
        self.audit_logs.insert(0, log_entry)
        if len(self.audit_logs) > 300:
            self.audit_logs.pop()
        if is_threat:
            self.metrics["total_threats_blocked"] += 1

    def record_login_attempt(self, ip: str, username: str, success: bool):
        now = time.time()
        if success:
            self.unblock_ip(ip)
            self.log_event(ip, "LOGIN_SUCCESS", f"Đăng nhập an toàn tài khoản [{username}]", is_threat=False, category="auth")
        else:
            self.failed_logins[ip].append(now)
            self.failed_logins[ip] = [t for t in self.failed_logins[ip] if now - t < 600]
            fail_count = len(self.failed_logins[ip])
            self.log_event(ip, "LOGIN_FAILED", f"Sai thông tin đăng nhập [{username}] (Lần {fail_count}/5)", is_threat=True, category="bruteforce")
            
            if fail_count >= 5:
                self.block_ip(ip, duration_seconds=900, reason="Thử dò mật khẩu quá 5 lần (Brute-force protection)", category="bruteforce_blocked")
                return True
        return False

    def inspect_request(self, request: Request, body_bytes: bytes = b"") -> tuple[bool, str]:
        ip = self.get_client_ip(request)
        now = time.time()
        path = request.url.path.lower()

        # LỚP 1: KIỂM TRA BẪY HONEYPOT (Phát hiện bot dò cổng ngầm)
        if path in HONEYPOT_PATHS or any(path.startswith(hp) for hp in ["/wp-", "/phpmy", "/.git", "/.env"]):
            self.block_ip(ip, duration_seconds=86400, reason=f"Truy cập bẫy Honeypot đường dẫn cấm: {path}", category="honeypot_trapped")
            return False, "Cảnh báo an ninh: Phát hiện hành vi thăm dò trái phép. IP đã bị khóa tự động."

        is_login_endpoint = (
            request.url.path in ["/api/auth/login", "/", "/favicon.ico", "/api/auth/me", "/sw.js", "/manifest.json"]
            or request.url.path.startswith("/static/")
            or request.url.path.startswith("/uploads/")
        )

        # LỚP 1 & 4: KIỂM TRA IP BLACKLIST (Ngoại trừ trang login để người dùng hợp lệ unblock)
        if not is_login_endpoint and self.is_ip_blocked(ip):
            return False, "IP của bạn đã bị tường lửa tạm khóa do phát hiện hành vi bất thường."

        # LỚP 1: KIỂM TRA SCANNER BOT
        ua = request.headers.get("User-Agent", "").lower()
        for bad_ua in BLOCKED_USER_AGENTS:
            if bad_ua in ua:
                self.block_ip(ip, duration_seconds=3600, reason=f"Công cụ quét tự động: {bad_ua}", category="scanners_blocked")
                return False, f"Chặn truy cập: Phát hiện công cụ quét bảo mật ({bad_ua})."

        # LỚP 2: ADAPTIVE RATE LIMITING & CHỐNG DDOS
        if request.url.path == "/api/auth/login":
            self.auth_request_history[ip].append(now)
            self.auth_request_history[ip] = [t for t in self.auth_request_history[ip] if now - t < 60]
            if len(self.auth_request_history[ip]) > 10:
                self.block_ip(ip, duration_seconds=300, reason="Gửi yêu cầu đăng nhập dồn dập (Anti-Bruteforce Rate Limit)", category="ddos_rate_limited")
                return False, "Tần suất đăng nhập quá nhanh. Vui lòng chờ 5 phút."

        self.request_history[ip].append(now)
        self.request_history[ip] = [t for t in self.request_history[ip] if now - t < 60]
        if len(self.request_history[ip]) > 180:
            self.block_ip(ip, duration_seconds=300, reason="Spam request quá mức (DDoS burst protection)", category="ddos_rate_limited")
            return False, "Tần suất truy cập quá nhanh. Tường lửa đã tạm ngắt kết nối trong 5 phút."

        # LỚP 3: DEEP WAF INSPECTION (URL Path & Query Parameters)
        full_path = request.url.path + ("?" + request.url.query if request.url.query else "")
        for pattern in MALICIOUS_PATTERNS:
            if pattern.search(full_path):
                self.block_ip(ip, duration_seconds=3600, reason="Mã độc trong URL (SQLi/XSS/Traversal)", category="sqli_blocked")
                return False, "Yêu cầu bị chặn: Phát hiện mã độc trong đường dẫn."

        # LỚP 3: DEEP WAF INSPECTION (Body Content)
        if body_bytes and len(body_bytes) < 50000 and request.url.path != "/api/assistant/execute":
            try:
                body_str = body_bytes.decode("utf-8", errors="ignore")
                for pattern in MALICIOUS_PATTERNS:
                    if pattern.search(body_str):
                        self.block_ip(ip, duration_seconds=3600, reason="Mã độc trong nội dung truyền tải", category="sqli_blocked")
                        return False, "Dữ liệu bị từ chối: Phát hiện ký tự tấn công OWASP."
            except Exception:
                pass

        return True, ""

firewall_manager = SecurityFirewallManager()

class SecurityFirewallMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/static/") and not request.url.path.endswith((".php", ".asp", ".env")):
            response = await call_next(request)
            response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
            return self.apply_security_headers(response)

        body = b""
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive

        is_safe, error_message = firewall_manager.inspect_request(request, body)
        if not is_safe:
            ip = firewall_manager.get_client_ip(request)
            return JSONResponse(
                status_code=403,
                content={
                    "error": "SECURITY_BLOCK",
                    "detail": error_message,
                    "firewall": "Truong Phat 7-Layer Enterprise Shield v5.0",
                    "client_ip": ip,
                    "timestamp": datetime.now().isoformat()
                }
            )

        response = await call_next(request)
        return self.apply_security_headers(response)

    # LỚP 6: TIÊU ĐỀ HTTP BẢO MẬT CHUẨN QUỐC TẾ (MILITARY-GRADE HEADERS)
    def apply_security_headers(self, response: Response) -> Response:
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval';"
        if "server" in response.headers:
            del response.headers["server"]
        response.headers["Server"] = "TruongPhat-Enterprise-Shield-v5.0"
        return response
