import re
import time
from collections import defaultdict
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime

# DANH SÁCH MẪU TẤN CÔNG ĐỘC HẠI PHỔ BIẾN (SQLi, XSS, Path Traversal, Command Injection)
MALICIOUS_PATTERNS = [
    # SQL Injection patterns
    re.compile(r"(\bunion\b.*\bselect\b|\bselect\b.*\bfrom\b|\binsert\b.*\binto\b|\bdelete\b.*\bfrom\b|\bdrop\b\s+(table|database))", re.IGNORECASE),
    re.compile(r"(--|#|/\*|\*/|;\s*waitfor\b|\bor\b\s+1\s*=\s*1\b|\band\b\s+1\s*=\s*1\b)", re.IGNORECASE),
    re.compile(r"(\bexec\s+sp_|\bxp_cmdshell\b|\bsp_executesql\b)", re.IGNORECASE),
    
    # Path Traversal & LFI/RFI
    re.compile(r"(\.\./|\.\.\\|/etc/passwd|/proc/self|/windows/win\.ini)", re.IGNORECASE),
    
    # Cross-Site Scripting (XSS)
    re.compile(r"(<script\b|javascript:|onerror\s*=|onload\s*=|alert\(|<iframe\b|<object\b)", re.IGNORECASE),
    
    # Shell / Remote Code Execution
    re.compile(r"(/bin/sh|/bin/bash|cmd\.exe|powershell|wget\s+|curl\s+http)", re.IGNORECASE)
]

# DANH SÁCH BOT / SCANNER QUỐC TẾ BỊ CHẶN TUYỆT ĐỐI
BLOCKED_USER_AGENTS = [
    "sqlmap", "nikto", "dirbuster", "masscan", "zgrab", "gobuster",
    "wprecon", "nmap", "acunetix", "havij", "metasploit", "censys",
    "shodan"
]

class SecurityFirewallManager:
    def __init__(self):
        self.request_history = defaultdict(list)
        self.failed_logins = defaultdict(list)
        self.blocked_ips = {}
        self.audit_logs = []
        self.total_attacks_blocked = 0

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

    def block_ip(self, ip: str, duration_seconds: int = 900, reason: str = "Tấn công độc hại"):
        self.blocked_ips[ip] = time.time() + duration_seconds
        self.log_event(ip, "IP_BLOCKED", f"Khóa IP {duration_seconds//60} phút. Lý do: {reason}", is_threat=True)

    def unblock_ip(self, ip: str):
        if ip in self.blocked_ips:
            del self.blocked_ips[ip]
        if ip in self.failed_logins:
            del self.failed_logins[ip]

    def log_event(self, ip: str, event_type: str, details: str, is_threat: bool = False):
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
            "ip": ip,
            "event_type": event_type,
            "details": details,
            "is_threat": is_threat
        }
        self.audit_logs.insert(0, log_entry)
        if len(self.audit_logs) > 300:
            self.audit_logs.pop()
        if is_threat:
            self.total_attacks_blocked += 1

    def record_login_attempt(self, ip: str, username: str, success: bool):
        now = time.time()
        if success:
            self.unblock_ip(ip)
            self.log_event(ip, "LOGIN_SUCCESS", f"Đăng nhập an toàn tài khoản [{username}]", is_threat=False)
        else:
            self.failed_logins[ip].append(now)
            self.failed_logins[ip] = [t for t in self.failed_logins[ip] if now - t < 600]
            fail_count = len(self.failed_logins[ip])
            self.log_event(ip, "LOGIN_FAILED", f"Sai thông tin đăng nhập [{username}] (Lần {fail_count}/5)", is_threat=True)
            
            if fail_count >= 5:
                self.block_ip(ip, duration_seconds=900, reason="Thử dò mật khẩu quá 5 lần (Brute-force protection)")
                return True
        return False

    def inspect_request(self, request: Request, body_bytes: bytes = b"") -> tuple[bool, str]:
        ip = self.get_client_ip(request)
        now = time.time()

        # Cho phép trang chủ và endpoint login để người dùng hợp lệ tự đăng nhập và giải phóng IP
        is_login_endpoint = request.url.path in ["/api/auth/login", "/", "/favicon.ico"]

        # 1. Kiểm tra IP Blacklist (ngoại trừ trang login)
        if not is_login_endpoint and self.is_ip_blocked(ip):
            return False, "IP của bạn đã bị tường lửa tạm khóa 15 phút do phát hiện hành vi bất thường."

        # 2. Kiểm tra User-Agent độc hại
        ua = request.headers.get("User-Agent", "").lower()
        for bad_ua in BLOCKED_USER_AGENTS:
            if bad_ua in ua:
                self.block_ip(ip, duration_seconds=1800, reason=f"Sử dụng công cụ quét bảo mật: {bad_ua}")
                return False, f"Chặn truy cập: Phát hiện công cụ quét tự động ({bad_ua})."

        # 3. Rate Limiting
        self.request_history[ip].append(now)
        self.request_history[ip] = [t for t in self.request_history[ip] if now - t < 60]
        if len(self.request_history[ip]) > 160:
            self.block_ip(ip, duration_seconds=300, reason="Spam request quá mức (DDoS protection)")
            return False, "Tần suất truy cập quá nhanh. Tường lửa đã tạm ngắt kết nối trong 5 phút."

        # 4. Kiểm tra URL & Query Parameters
        full_path = str(request.url)
        for pattern in MALICIOUS_PATTERNS:
            if pattern.search(full_path):
                self.block_ip(ip, duration_seconds=3600, reason="Phát hiện mã độc trong URL (SQLi/XSS)")
                return False, "Yêu cầu bị chặn: Phát hiện mã độc trong đường dẫn."

        # 5. Kiểm tra Body (Ngoại trừ cổng chat trợ lý AI hội thoại tiếng Việt)
        if body_bytes and len(body_bytes) < 50000 and request.url.path != "/api/assistant/execute":
            try:
                body_str = body_bytes.decode("utf-8", errors="ignore")
                for pattern in MALICIOUS_PATTERNS:
                    if pattern.search(body_str):
                        self.block_ip(ip, duration_seconds=3600, reason="Phát hiện mã độc trong nội dung truyền tải")
                        return False, "Dữ liệu bị từ chối: Phát hiện ký tự tấn công SQLi/XSS."
            except Exception:
                pass

        return True, ""

firewall_manager = SecurityFirewallManager()

class SecurityFirewallMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/static/") and not request.url.path.endswith((".php", ".asp", ".env")):
            response = await call_next(request)
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
                    "firewall": "Truong Phat Enterprise WAF Shield v3.5",
                    "client_ip": ip,
                    "timestamp": datetime.now().isoformat()
                }
            )

        response = await call_next(request)
        return self.apply_security_headers(response)

    def apply_security_headers(self, response: Response) -> Response:
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        if "server" in response.headers:
            del response.headers["server"]
        response.headers["Server"] = "Enterprise-Secure-Gateway"
        return response
