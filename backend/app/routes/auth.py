from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database.connection import get_db
from app.models import User
from app.schemas import LoginRequest, Token, UserResponse
from app.utils.auth import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.

    Demo Credentials:
    - manager@resort360.com / password123 (MANAGER)
    - frontdesk@resort360.com / password123 (FRONT_DESK)
    - housekeeping.head@resort360.com / password123 (DEPARTMENT_HEAD)
    - maintenance.head@resort360.com / password123 (DEPARTMENT_HEAD)
    - fb.head@resort360.com / password123 (DEPARTMENT_HEAD)
    - inventory.head@resort360.com / password123 (DEPARTMENT_HEAD)
    - staff.elena@resort360.com / password123 (STAFF)
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )

    # Return token with user data
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "resort_id": user.resort_id,
            "department_id": user.department_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "phone": user.phone,
            "avatar_url": user.avatar_url
        }
    }
