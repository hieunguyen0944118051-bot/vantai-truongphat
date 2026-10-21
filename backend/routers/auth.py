import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import get_db
from login_guard import client_ip, login_guard

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

PIN_KEYS = ("security_pin", "security_pin_code")


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdatePinRequest(BaseModel):
    old_pin: str
    new_pin: str


def expected_pin(db: Session):
    """Mã PIN cấp 2: biến môi trường SECURITY_PIN (ưu tiên, không mất khi deploy) hoặc giá trị trong DB.
    Không có mã PIN dự phòng nào ghi cứng trong code."""
    env_pin = (os.environ.get("SECURITY_PIN") or "").strip()
    if env_pin:
        return env_pin
    st = db.query(models.SystemSetting).filter(models.SystemSetting.key.in_(PIN_KEYS)).first()
    return st.value.strip() if st and st.value and st.value.strip() else None


@router.post("/login", response_model=schemas.Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    ip = client_ip(request)
    username = form_data.username.strip().lower()
    password = form_data.password.strip()

    wait = login_guard.seconds_locked(ip, username)
    if wait:
        raise HTTPException(status_code=429, detail=f"Sai quá nhiều lần. Thử lại sau {wait // 60 + 1} phút.")

    user = db.query(models.User).filter(models.User.username == username).first()
    password_ok = bool(user) and auth.verify_password(password, user.password_hash)

    pin_required = expected_pin(db)
    client_pin = (request.headers.get("X-Security-PIN") or request.query_params.get("pin") or "").strip()
    pin_ok = (pin_required is None) or (client_pin == pin_required)

    if not (password_ok and pin_ok):
        login_guard.record_failure(ip, username)
        if not password_ok:
            msg = "Tên đăng nhập hoặc mật khẩu không chính xác!"
        elif not client_pin:
            msg = "Vui lòng nhập mã PIN bảo mật cấp 2!"
        else:
            msg = "Mã PIN bảo mật cấp 2 không chính xác!"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg,
                            headers={"WWW-Authenticate": "Bearer"})

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản này đã bị vô hiệu hóa")

    login_guard.record_success(ip, username)
    token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role},
    }


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, db: Session = Depends(get_db),
                    current_user: models.User = Depends(auth.get_current_user)):
    if not auth.verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác!")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải có tối thiểu 8 ký tự!")
    current_user.password_hash = auth.get_password_hash(req.new_password)
    db.commit()
    return {"message": "Đã đổi mật khẩu thành công!"}


@router.post("/update-pin")
def update_pin(req: UpdatePinRequest, db: Session = Depends(get_db),
               current_user: models.User = Depends(auth.require_role(["admin"]))):
    """Đổi mã PIN cấp 2 (chỉ admin). Nếu đã đặt SECURITY_PIN trên Render thì đổi ở Render."""
    if (os.environ.get("SECURITY_PIN") or "").strip():
        raise HTTPException(status_code=400,
                            detail="Mã PIN đang đặt bằng biến môi trường SECURITY_PIN trên Render — hãy đổi tại đó.")
    current = expected_pin(db)
    if current is not None and req.old_pin.strip() != current:
        raise HTTPException(status_code=400, detail="Mã PIN hiện tại không chính xác!")
    new_pin = req.new_pin.strip()
    if len(new_pin) < 6:
        raise HTTPException(status_code=400, detail="Mã PIN mới phải có tối thiểu 6 ký tự!")
    st = db.query(models.SystemSetting).filter(models.SystemSetting.key.in_(PIN_KEYS)).first()
    if st:
        st.value = new_pin
    else:
        db.add(models.SystemSetting(key="security_pin", value=new_pin))
    db.commit()
    return {"success": True, "message": "Đã đổi mã PIN. Lưu ý: deploy lại sẽ quay về mã cũ nếu chưa đặt SECURITY_PIN trên Render."}
