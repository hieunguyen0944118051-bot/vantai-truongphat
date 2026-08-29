from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import models, schemas, auth
from database import get_db

from datetime import datetime, timedelta

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory brute force protection: username -> [timestamps]
failed_attempts = {}

def check_rate_limit(username: str):
    now = datetime.now()
    attempts = failed_attempts.get(username, [])
    # Filter attempts within last 15 minutes
    recent = [t for t in attempts if now - t < timedelta(minutes=15)]
    failed_attempts[username] = recent
    if len(recent) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Tài khoản bị tạm khóa 15 phút do nhập sai mật khẩu quá 5 lần để đảm bảo an ninh hệ thống!"
        )

def record_failed_attempt(username: str):
    now = datetime.now()
    if username not in failed_attempts:
        failed_attempts[username] = []
    failed_attempts[username].append(now)

def clear_failed_attempts(username: str):
    if username in failed_attempts:
        del failed_attempts[username]

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    clean_username = form_data.username.strip().lower()
    check_rate_limit(clean_username)

    user = db.query(models.User).filter(models.User.username == clean_username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        record_failed_attempt(clean_username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác!",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản này đã bị vô hiệu hóa")
    
    clear_failed_attempts(clean_username)
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
    req: schemas.ChangePasswordRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác!")
    
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Mật khẩu mới và xác nhận mật khẩu không trùng khớp!")
    
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải có tối thiểu 6 ký tự để đảm bảo an toàn!")
    
    current_user.password_hash = auth.get_password_hash(req.new_password)
    db.commit()
    return {"success": True, "message": "Đã đổi mật khẩu thành công! Hãy dùng mật khẩu mới trong các lần đăng nhập tiếp theo."}

