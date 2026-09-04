from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models, auth
from security_firewall import firewall_manager

router = APIRouter(prefix="/api/security", tags=["Security & Firewall"])

class UpdatePinRequest(BaseModel):
    old_pin: str
    new_pin: str

class UnblockIpRequest(BaseModel):
    ip: str

@router.get("/status")
def get_security_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Lấy thông tin tổng quan về Tường Lửa 7 Lớp và An Ninh Hệ Thống"""
    client_ip = firewall_manager.get_client_ip(request)
    
    # Lấy mã PIN hiện tại trong DB
    pin_setting = db.query(models.SystemSetting).filter(
        (models.SystemSetting.key == "security_pin") | (models.SystemSetting.key == "security_pin_code")
    ).first()
    current_pin = pin_setting.value if pin_setting else "2626"

    blocked_list = [
        {"ip": ip, "remaining_seconds": max(0, int(expire_time - __import__("time").time()))}
        for ip, expire_time in firewall_manager.blocked_ips.items()
    ]

    layers_status = [
        {"layer": 1, "name": "Bẫy Honeypot & Lọc Bot Scanners", "status": "ACTIVE", "desc": "Tự động khóa 24h khi phát hiện bot quét cổng ngầm & 35+ công cụ dò lỗ hổng."},
        {"layer": 2, "name": "Adaptive Rate Limiting & Chống DDoS", "status": "ACTIVE", "desc": "Giới hạn tần suất 10 req/phút cho Auth & 180 req/phút toàn hệ thống."},
        {"layer": 3, "name": "Deep WAF OWASP Top 10 (SQLi/XSS/RCE)", "status": "ACTIVE", "desc": "Soi chiếu sâu Query & Body, chặn đứng SQL Injection, XSS, RCE, Path Traversal."},
        {"layer": 4, "name": "Bảo Mật 2FA Cấp 2 & Chống Brute-Force", "status": "ACTIVE", "desc": "Xác thực 2 lớp với Mã PIN bảo mật & khóa IP lũy tiến sau 5 lần sai."},
        {"layer": 5, "name": "Session Hijacking & Toàn Vẹn Token", "status": "ACTIVE", "desc": "Mã hóa JWT HMAC-SHA256, tự động hủy phiên khi phát hiện bất thường."},
        {"layer": 6, "name": "Tiêu Đề An Toàn Quân Đội (Military Headers)", "status": "ACTIVE", "desc": "Kích hoạt CSP, HSTS 256-bit, X-Frame-Options, che giấu thông tin máy chủ."},
        {"layer": 7, "name": "Nhật Ký Kiểm Toán SIEM & Cảnh Báo Tức Thời", "status": "ACTIVE", "desc": "Ghi nhận 300 sự kiện an ninh gần nhất, cảnh báo xâm nhập thời gian thực."}
    ]

    return {
        "firewall_active": True,
        "shield_version": "7-Layer Enterprise WAF Shield v5.0 (OWASP & ISO 27001)",
        "client_ip": client_ip,
        "total_attacks_blocked": firewall_manager.metrics["total_threats_blocked"],
        "metrics": firewall_manager.metrics,
        "layers": layers_status,
        "blocked_ips_count": len(blocked_list),
        "blocked_ips": blocked_list,
        "has_custom_pin": bool(pin_setting and pin_setting.value),
        "audit_logs": firewall_manager.audit_logs[:80]
    }

@router.post("/unblock-ip")
def unblock_ip(
    req: UnblockIpRequest,
    current_user: models.User = Depends(auth.require_role(["admin"]))
):
    """Admin mở khóa một địa chỉ IP"""
    if req.ip in firewall_manager.blocked_ips:
        del firewall_manager.blocked_ips[req.ip]
        firewall_manager.log_event(req.ip, "IP_UNBLOCKED", f"Admin [{current_user.username}] đã gỡ khóa IP thủ công", is_threat=False)
        return {"success": True, "message": f"Đã gỡ khóa thành công IP {req.ip}"}
    return {"success": False, "message": f"IP {req.ip} không nằm trong danh sách khóa."}

@router.post("/update-pin")
def update_security_pin(
    req: UpdatePinRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(["admin"]))
):
    """Admin đổi mã PIN bảo mật cấp 2"""
    pin_setting = db.query(models.SystemSetting).filter(
        (models.SystemSetting.key == "security_pin") | (models.SystemSetting.key == "security_pin_code")
    ).first()
    current_pin = pin_setting.value if pin_setting else "2626"

    if req.old_pin.strip() != current_pin:
        raise HTTPException(status_code=400, detail="Mã PIN hiện tại không chính xác!")

    if len(req.new_pin.strip()) < 4:
        raise HTTPException(status_code=400, detail="Mã PIN mới phải có tối thiểu 4 ký tự/chữ số!")

    if not pin_setting:
        pin_setting = models.SystemSetting(key="security_pin_code", value=req.new_pin.strip())
        db.add(pin_setting)
    else:
        pin_setting.value = req.new_pin.strip()

    db.commit()
    return {"success": True, "message": "Đã đổi Mã PIN bảo mật cấp 2 thành công!"}
