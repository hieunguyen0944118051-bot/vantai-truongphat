from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import models
from database import get_db

SECRET_KEY = "antigravity-transport-secret-key-2026-super-secure"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12 # 12 hours according to Lenh 2

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    # 1. Direct bcrypt check (always reliable across all platforms)
    try:
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"bcrypt.checkpw error: {e}")

    # 2. Passlib fallback
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"passlib.verify error: {e}")

    # 3. Plaintext fallback if needed
    return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    try:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    except Exception:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    """Xác thực người dùng từ Bearer Authorization header hoặc Cookie httpOnly."""
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        # Fallback query param for image signed urls / print views
        token = request.query_params.get("token")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Chưa đăng nhập hoặc phiên làm việc đã hết hạn. Vui lòng đăng nhập lại!",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản này đã bị vô hiệu hóa")
    return user

def require_role(roles: list):
    def role_checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này"
            )
        return current_user
    return role_checker

def require_salan_role(*allowed_roles):
    """Kiểm tra vai trò cho module sà lan (quan_tri, nhap_van_hanh, ke_toan, ban_giam_doc, chu_hang)."""
    def checker(current_user: models.User = Depends(get_current_user)):
        user_role = current_user.get_salan_role()
        if user_role == "quan_tri":
            return current_user
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền hạn không đủ! Vai trò '{user_role}' không được phép truy cập chức năng này."
            )
        return current_user
    return checker

def require_salan_write_permission(current_user: models.User = Depends(get_current_user)):
    """Chặn vai trò chỉ xem (ban_giam_doc) ghi dữ liệu."""
    user_role = current_user.get_salan_role()
    if user_role == "ban_giam_doc":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ban Giám Đốc chỉ có quyền xem, không được thêm/sửa/xoá trực tiếp dữ liệu chuyến!"
        )
    return current_user
