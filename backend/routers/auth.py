from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import models, schemas, auth
from database import get_db
from datetime import datetime, timedelta
from security_firewall import firewall_manager

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/login", response_model=schemas.Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    ip = firewall_manager.get_client_ip(request)

    # 1. Kiểm tra IP có đang bị tường lửa khóa không
    if firewall_manager.is_ip_blocked(ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Địa chỉ IP của bạn đã bị tường lửa tạm khóa 15 phút do nhập sai quá nhiều lần!"
        )

    clean_username = form_data.username.strip().lower()
    clean_password = form_data.password.strip()

    # 2. Đảm bảo tài khoản admin luôn sẵn sàng
    user = db.query(models.User).filter(models.User.username == clean_username).first()
    if not user and clean_username == "admin":
        user = models.User(
            username="admin",
            password_hash=auth.get_password_hash("admin123"),
            full_name="Ban Giám Đốc (Trường Phát)",
            role="admin",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Lấy mã PIN bảo mật cấp 2 (Mặc định 2626)
    pin_setting = db.query(models.SystemSetting).filter(
        (models.SystemSetting.key == "security_pin") | (models.SystemSetting.key == "security_pin_code")
    ).first()
    expected_pin = pin_setting.value if pin_setting else "2626"

    # Kiểm tra mã PIN được gửi qua Header hoặc Form
    client_pin = request.headers.get("X-Security-PIN") or request.query_params.get("pin")

    # Xác thực mật khẩu
    password_ok = user and auth.verify_password(clean_password, user.password_hash)

    # Nếu có mã PIN truyền lên thì kiểm tra khớp, hoặc bắt buộc nếu được gửi
    pin_ok = (client_pin.strip() == expected_pin) if client_pin else (expected_pin == "2626")

    if not password_ok or not pin_ok:
        is_now_blocked = firewall_manager.record_login_attempt(ip, clean_username, success=False)
        if is_now_blocked:
            detail_msg = "Bạn đã nhập sai thông tin 5 lần! IP đã bị tường lửa khóa 15 phút để chống tấn công dò mật khẩu."
        elif not password_ok:
            detail_msg = "Tên đăng nhập hoặc mật khẩu không chính xác!"
        else:
            detail_msg = "Mã PIN bảo mật cấp 2 không chính xác!"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản này đã bị vô hiệu hóa")

    # Đăng nhập thành công -> Ghi nhật ký & Xóa các lần thử sai
    firewall_manager.record_login_attempt(ip, clean_username, success=True)
    access_token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if not auth.verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không chính xác!"
        )

    if len(req.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải có tối thiểu 6 ký tự!"
        )

    current_user.password_hash = auth.get_password_hash(req.new_password)
    db.commit()
    return {"message": "Đã đổi mật khẩu thành công! Vui lòng ghi nhớ mật khẩu mới."}
