import re
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from jose import JWTError, jwt
import uuid

from app.models.user import User
from app.core.config import settings


class AuthService:
    """Service for handling authentication-related operations."""
    
    # Email whitelist for signup restrictions
    WHITELISTED_EMAILS = {
        "ethan@smartscalingai.com",
        "ek@alienunderpants.io", 
        "test@domain.com",
        "test@example.com",
    }
    
    # JWT Configuration
    SECRET_KEY = getattr(settings, 'SECRET_KEY', 'your-secret-key-here')  # Add to config
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    @staticmethod
    def hash_password(password: str) -> bytes:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    @staticmethod
    def verify_password(password: str, hashed_password: bytes) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password if isinstance(hashed_password, bytes) else hashed_password.encode('utf-8')
            )
        except Exception:
            return False

    @classmethod
    def is_email_whitelisted(cls, email: str) -> bool:
        """Check if email is whitelisted for signup."""
        email_lower = email.lower()
        return (email_lower in cls.WHITELISTED_EMAILS or 
                email_lower.endswith("@hellacooltestingdomain.pizza"))

    @classmethod
    def create_access_token(cls, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return encoded_jwt

    @classmethod
    def verify_token(cls, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def signup(self, email: str, password: str, confirm_password: str, db: Session) -> Dict[str, Any]:
        """Register a new user."""
        # Check email whitelist
        if not self.is_email_whitelisted(email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This email is not allowed to sign up."
            )

        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        hashed_password = self.hash_password(password)
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            password=hashed_password,
            name=""
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return {
            "message": "User registered successfully",
            "user": user.to_dict()
        }

    def login(self, email: str, password: str, db: Session) -> Dict[str, Any]:
        """Authenticate user and return token."""
        # Find user
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user or not self.verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Create access token
        access_token_expires = timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"user_id": user.id}, expires_delta=access_token_expires
        )

        return {
            "message": "Login successful",
            "token": {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": self.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            },
            "user": user.to_dict()
        }

    def get_current_user(self, token: str, db: Session) -> User:
        """Get current user from token."""
        payload = self.verify_token(token)
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user 