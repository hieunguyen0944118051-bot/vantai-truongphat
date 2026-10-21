import os
import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import auth
import models
from database import Base, SessionLocal, engine
from login_guard import SecurityHeadersMiddleware
from routers import assistant, barges, dashboard, drivers, fuel, gps, maintenance, trips, users, vehicles
from routers import auth as auth_router

try:
    from routers import weighbridge
except ImportError:
    weighbridge = None

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hệ Thống Quản Lý Vận Tải Xe Đầu Kéo & Sà Lan - Trường Phát",
    version="3.6.0",
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(SecurityHeadersMiddleware)
# Chỉ trang của chính app gọi API (cùng tên miền) — không mở cho trang khác.
_allowed = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _allowed:
    app.add_middleware(CORSMiddleware, allow_origins=_allowed, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

for r in (auth_router, users, vehicles, barges, drivers, trips, fuel, dashboard, maintenance, assistant, gps):
    app.include_router(r.router)
if weighbridge:
    app.include_router(weighbridge.router)

static_path = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}


@app.get("/")
def serve_ui():
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, headers=NO_CACHE)
    return {"message": "Hệ thống Quản lý Vận tải đang hoạt động!"}


@app.get("/sw.js")
def serve_service_worker():
    return FileResponse(os.path.join(static_path, "sw.js"), media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", **NO_CACHE})


@app.get("/manifest.json")
def serve_manifest():
    return FileResponse(os.path.join(static_path, "manifest.json"), media_type="application/manifest+json")


@app.on_event("startup")
def init_accounts():
    """Tài khoản quản trị.

    - ADMIN_PASSWORD (biến môi trường Render): nếu có, đặt lại mật khẩu tài khoản 'admin' mỗi lần khởi động.
      Đây là cách đổi mật khẩu bền vững khi DB còn nằm trong repo (deploy lại không mất).
    - DB chưa có tài khoản nào: tạo 'admin' với mật khẩu ngẫu nhiên in ra log Render.
    Không còn mật khẩu mặc định nào trong code.
    """
    db = SessionLocal()
    try:
        env_pw = os.environ.get("ADMIN_PASSWORD")
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if admin and env_pw:
            admin.password_hash = auth.get_password_hash(env_pw)
            db.commit()
            print("[auth] Đã đặt mật khẩu admin theo ADMIN_PASSWORD.")
        elif not admin and db.query(models.User).count() == 0:
            pw = env_pw or secrets.token_urlsafe(12)
            db.add(models.User(username="admin", password_hash=auth.get_password_hash(pw),
                               full_name="Ban Giám Đốc (Trường Phát)", role="admin", is_active=True))
            db.commit()
            if not env_pw:
                print(f"[auth] Đã tạo tài khoản admin, mật khẩu tạm: {pw} — đổi ngay sau khi đăng nhập.")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
