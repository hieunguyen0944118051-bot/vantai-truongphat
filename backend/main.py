import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base, SessionLocal
import models, auth
from routers import auth as auth_router, users, vehicles, barges, drivers, trips, fuel, dashboard, maintenance, assistant, gps, traffic_fines, security, salan
from security_firewall import SecurityFirewallMiddleware, firewall_manager

try:
    from routers import weighbridge
except ImportError:
    weighbridge = None

from fastapi import Request
Base.metadata.create_all(bind=engine)

# Trang tài liệu API (/docs) chỉ mở khi chạy thử trên máy: APP_ENV=dev. Mặc định tắt trên máy chủ thật.
is_prod = os.environ.get("APP_ENV", "production").lower() != "dev"

app = FastAPI(
    title="Hệ Thống Quản Lý Vận Tải Xe Đầu Kéo & Sà Lan - Trường Phát",
    description="API quản lý đội xe 26 đầu kéo, rơ-mooc, 10 sà lan & Tích hợp GPS Bình Anh",
    version="3.5.0",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json"
)

# 0. Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

# 1. GZip Compression Middleware (Nén dữ liệu JSON/HTML/JS giảm 85% dung lượng, load nhanh gấp 5-10 lần)
app.add_middleware(GZipMiddleware, minimum_size=500)

# 2. Tường Lửa Bảo Mật Ứng Dụng WAF (Chặn Brute-Force, DDoS, SQLi, XSS, Scanner Bots)
app.add_middleware(SecurityFirewallMiddleware)

# 3. CORS Middleware
# Chỉ cho các địa chỉ trong ALLOWED_ORIGINS gọi API từ trang khác (phân cách dấu phẩy).
# App tự gọi chính nó không cần CORS, nên mặc định không mở cho trang nào.
_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Security-PIN"],
    )

app.include_router(auth_router.router)
app.include_router(security.router)
app.include_router(users.router)
app.include_router(vehicles.router)
app.include_router(barges.router)
app.include_router(drivers.router)
app.include_router(trips.router)
app.include_router(fuel.router)
app.include_router(dashboard.router)
app.include_router(maintenance.router)
app.include_router(assistant.router)
app.include_router(gps.router)
app.include_router(traffic_fines.router)
app.include_router(salan.router)
if weighbridge:
    app.include_router(weighbridge.router)

# Mount static folder
static_path = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Thư mục uploads (ảnh chứng từ) KHÔNG mở công khai — chỉ xem qua API có kiểm tra đăng nhập.
upload_path = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(upload_path, exist_ok=True)

@app.get("/")
def serve_ui():
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "Hệ thống Quản lý Vận tải đang hoạt động!"}

@app.get("/sw.js")
def serve_service_worker():
    sw_file = os.path.join(static_path, "sw.js")
    if os.path.exists(sw_file):
        return FileResponse(sw_file, media_type="application/javascript", headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"error": "sw not found"}

@app.get("/manifest.json")
def serve_manifest():
    manifest_file = os.path.join(static_path, "manifest.json")
    if os.path.exists(manifest_file):
        return FileResponse(manifest_file, media_type="application/manifest+json")
    return {"error": "manifest not found"}

@app.get("/weighbridge")
def serve_weighbridge_ui():
    wb_file = os.path.join(static_path, "weighbridge.html")
    if os.path.exists(wb_file):
        return FileResponse(wb_file)
    return FileResponse(os.path.join(static_path, "index.html"))

@app.get("/salan")
def serve_salan_ui():
    salan_file = os.path.join(static_path, "salan.html")
    if os.path.exists(salan_file):
        return FileResponse(salan_file, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "Salan UI file not found"}

@app.on_event("startup")
def init_db():
    """Tài khoản: không có mật khẩu mặc định trong code.
    - ADMIN_PASSWORD (Render): đặt lại mật khẩu tài khoản 'admin' mỗi lần khởi động.
    - USER_PASSWORDS (Render, tùy chọn): "ten1=matkhau1;ten2=matkhau2" — đặt mật khẩu cho từng tài khoản.
      Dùng 1 lần để cấp mật khẩu mới cho nhân viên, sau đó xóa biến này và để nhân viên tự đổi."""
    import secrets as _secrets
    db = SessionLocal()
    try:
        env_admin = os.environ.get("ADMIN_PASSWORD")
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            pw = env_admin or _secrets.token_urlsafe(12)
            db.add(models.User(username="admin", password_hash=auth.get_password_hash(pw),
                               full_name="Ban Giám Đốc (Trường Phát)", role="admin", is_active=True))
            print("[auth] Đã tạo tài khoản admin" + ("" if env_admin else " với mật khẩu ngẫu nhiên — đặt ADMIN_PASSWORD trên Render để đăng nhập."))
        elif env_admin:
            admin.password_hash = auth.get_password_hash(env_admin)
            print("[auth] Đã đặt mật khẩu admin theo ADMIN_PASSWORD.")
        for pair in (os.environ.get("USER_PASSWORDS") or "").split(";"):
            if "=" not in pair:
                continue
            name, pw = pair.split("=", 1)
            u = db.query(models.User).filter(models.User.username == name.strip().lower()).first()
            if u and len(pw.strip()) >= 8:
                u.password_hash = auth.get_password_hash(pw.strip())
                print(f"[auth] Đã đặt mật khẩu mới cho {u.username} theo USER_PASSWORDS.")
        db.commit()
        weak = [u.username for u in db.query(models.User).all() if not (u.password_hash or "").startswith("$2")]
        if weak:
            print("[auth] Các tài khoản chưa có mật khẩu mã hóa — không đăng nhập được cho tới khi đặt qua USER_PASSWORDS: " + ", ".join(weak))
    finally:
        db.close()

    # Background cache warmup để mọi truy cập đầu tiên vào https://vantai-truongphat.onrender.com/ đạt tốc độ < 0.05s
    import threading
    from datetime import date
    from sheets_service import sheets_client
    def _warmup_sheets_cache():
        try:
            today_str = date.today().strftime("%Y-%m-%d")
            sheets_client.fetch_full_maintenance_and_fuel_workbook()
            sheets_client.fetch_daily_trips(today_str)
            sheets_client.get_weekly_dispatch_stats(today_str)
            sheets_client.fetch_daily_trips("2026-11-03")
            sheets_client.get_weekly_dispatch_stats("2026-11-03")
        except Exception as e:
            print(f"Warmup notice: {e}")
    threading.Thread(target=_warmup_sheets_cache, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
