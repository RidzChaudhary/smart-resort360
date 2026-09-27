from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import User
import os

APP_ENV = os.getenv("APP_ENV", "development").strip().casefold()
SECRET_KEY = os.getenv("SECRET_KEY")
if APP_ENV == "production":
    if not SECRET_KEY or len(SECRET_KEY) < 32:
        raise RuntimeError("A SECRET_KEY of at least 32 characters must be configured in production")
elif not SECRET_KEY:
    SECRET_KEY = "local-development-only-secret-key-do-not-deploy"
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours for demo

security = HTTPBearer()

DEPARTMENT_HEAD_DEPARTMENTS = frozenset({
    "housekeeping",
    "maintenance",
    "food & beverage",
    "inventory",
})

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password using bcrypt"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = decode_access_token(token)

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user

def require_role(allowed_roles: list):
    """Dependency factory to require specific user roles"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return current_user
    return role_checker

def get_department_head_department_id(current_user: User) -> int:
    """Return the validated department scope for an operational department head."""
    department = current_user.department
    if (
        current_user.role != "DEPARTMENT_HEAD"
        or department is None
        or department.id != current_user.department_id
        or department.resort_id != current_user.resort_id
        or department.name.strip().casefold() not in DEPARTMENT_HEAD_DEPARTMENTS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Department Head access is limited to Housekeeping, Maintenance, Food & Beverage, and Inventory",
        )
    return department.id

def require_department_head(current_user: User = Depends(get_current_user)) -> User:
    get_department_head_department_id(current_user)
    return current_user
