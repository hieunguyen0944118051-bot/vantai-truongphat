"""Bảo vệ đăng nhập + tiêu đề HTTP an toàn.

Thay cho "tường lửa 7 lớp" cũ (chặn nhầm ký tự #, --, /* trong ghi chú và khóa cả văn phòng).
Chỉ giữ 2 việc có tác dụng thật:
  1. Khóa tạm khi sai đăng nhập nhiều lần — theo IP VÀ theo tên đăng nhập
     (đổi IP giả không vượt được giới hạn theo tài khoản).
  2. Gắn các tiêu đề bảo mật chuẩn cho mọi phản hồi.
"""
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

WINDOW_SECONDS = 10 * 60      # đếm số lần sai trong 10 phút
MAX_FAILS_PER_IP = 5          # quá 5 lần sai / IP -> khóa IP
MAX_FAILS_PER_USER = 10       # quá 10 lần sai / tài khoản -> khóa tài khoản
LOCK_SECONDS = 15 * 60        # khóa 15 phút


def client_ip(request: Request) -> str:
    """IP người dùng sau proxy Render.

    Ưu tiên tiêu đề do Cloudflare/Render ghi đè; với X-Forwarded-For lấy phần tử CUỐI
    (do proxy gắn thêm), không lấy phần tử đầu (trình duyệt tự khai được).
    """
    for h in ("CF-Connecting-IP", "True-Client-IP"):
        v = request.headers.get(h)
        if v:
            return v.strip()
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class LoginGuard:
    def __init__(self):
        self._fails = defaultdict(list)   # key -> [thời điểm sai]
        self._locked = {}                 # key -> hết khóa lúc

    def _key_locked(self, key: str) -> int:
        until = self._locked.get(key)
        if until and until > time.time():
            return int(until - time.time())
        self._locked.pop(key, None)
        return 0

    def seconds_locked(self, ip: str, username: str) -> int:
        return max(self._key_locked(f"ip:{ip}"), self._key_locked(f"user:{username}"))

    def record_failure(self, ip: str, username: str):
        now = time.time()
        for key, limit in ((f"ip:{ip}", MAX_FAILS_PER_IP), (f"user:{username}", MAX_FAILS_PER_USER)):
            self._fails[key] = [t for t in self._fails[key] if now - t < WINDOW_SECONDS] + [now]
            if len(self._fails[key]) >= limit:
                self._locked[key] = now + LOCK_SECONDS
                self._fails[key] = []

    def record_success(self, ip: str, username: str):
        for key in (f"ip:{ip}", f"user:{username}"):
            self._fails.pop(key, None)


login_guard = LoginGuard()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
