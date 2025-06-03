from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    UserSignupRequest, UserLoginRequest, SignupResponse, 
    LoginResponse, UserResponse
)
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter()

@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserSignupRequest,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    auth_service = AuthService()
    result = auth_service.signup(
        email=user_data.email,
        password=user_data.password,
        confirm_password=user_data.confirm_password,
        db=db
    )
    return result

@router.post("/login", response_model=LoginResponse)
async def login(
    user_data: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user and return token."""
    auth_service = AuthService()
    result = auth_service.login(
        email=user_data.email,
        password=user_data.password,
        db=db
    )
    return result

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user.to_dict() 