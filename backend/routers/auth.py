from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import models, schemas, auth
from database import get_db
from datetime import datetime, timedelta
from security_firewall import firewall_manager
import security_pin

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/login", response_model=schemas.Token)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    ip = firewall_manager.get_client_ip(request)

    clean_username = form_data.username.strip().lower()
    clean_password = form_data.password.strip()

    user = db.query(models.User).filter(models.User.username == clean_username).first()

    # 2. Mã PIN cấp 2 (biến môi trường SECURITY_PIN hoặc giá trị trong CSDL — không có mã mặc định)
    expected_pin = security_pin.expected_pin(db)

    client_pin = request.headers.get("X-Security-PIN") or ""
    client_pin = str(client_pin).strip()

    password_ok = bool(user and auth.verify_password(clean_password, user.password_hash))
    pin_ok = bool(expected_pin) and bool(client_pin) and client_pin == expected_pin

    if password_ok and pin_ok and not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa. Liên hệ quản trị.")

    if password_ok and pin_ok:

        firewall_manager.unblock_ip(ip)
        firewall_manager.record_login_attempt(ip, clean_username, success=True)

        access_token = auth.create_access_token(data={"sub": user.username, "role": user.role})
        
        # Thiết lập cookie httpOnly bảo mật cho trình duyệt
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https",
            samesite="lax",
            max_age=43200
        )

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

    # NẾU SAI THÔNG TIN -> Ghi nhận lỗi
    is_now_blocked = firewall_manager.record_login_attempt(ip, clean_username, success=False)
    if is_now_blocked or firewall_manager.is_ip_blocked(ip):
        detail_msg = "Địa chỉ IP đã bị tạm khóa do nhập sai nhiều lần. Vui lòng kiểm tra lại tài khoản, mật khẩu và mã PIN!"
    elif not password_ok:
        detail_msg = "Tên đăng nhập hoặc mật khẩu không chính xác!"
    elif not expected_pin:
        detail_msg = "Máy chủ chưa cấu hình mã PIN cấp 2 (SECURITY_PIN). Liên hệ quản trị."
    elif not client_pin:
        detail_msg = "Vui lòng nhập mã PIN bảo mật cấp 2!"
    else:
        detail_msg = "Mã PIN bảo mật cấp 2 không chính xác!"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail_msg,
        headers={"WWW-Authenticate": "Bearer"},
    )

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
