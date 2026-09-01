import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base, SessionLocal
import models, auth
from routers import auth as auth_router, users, vehicles, barges, drivers, trips, fuel, dashboard, maintenance, assistant, gps, traffic_fines, security
from security_firewall import SecurityFirewallMiddleware, firewall_manager

try:
    from routers import weighbridge
except ImportError:
    weighbridge = None

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hệ Thống Quản Lý Vận Tải Xe Đầu Kéo & Sà Lan - Trường Phát",
    description="API quản lý đội xe 26 đầu kéo, rơ-mooc, 10 sà lan & Tích hợp GPS Bình Anh",
    version="3.5.0"
)

# 1. Tường Lửa Bảo Mật Ứng Dụng WAF (Chặn Brute-Force, DDoS, SQLi, XSS, Scanner Bots)
app.add_middleware(SecurityFirewallMiddleware)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
if weighbridge:
    app.include_router(weighbridge.router)

# Mount static folder
static_path = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Mount uploads folder
upload_path = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(upload_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")

@app.get("/")
def serve_ui():
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Hệ thống Quản lý Vận tải đang hoạt động!"}

@app.get("/weighbridge")
def serve_weighbridge_ui():
    wb_file = os.path.join(static_path, "weighbridge.html")
    if os.path.exists(wb_file):
        return FileResponse(wb_file)
    return FileResponse(os.path.join(static_path, "index.html"))

@app.on_event("startup")
def init_db():
    db = SessionLocal()
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        admin_user = models.User(
            username="admin",
            password_hash=auth.get_password_hash("admin123"),
            full_name="Ban Giám Đốc (Trường Phát)",
            role="admin",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print("Đã tạo tài khoản mặc định: admin / admin123")
    db.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
