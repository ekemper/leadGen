# Auth Business Logic Migration Guide

## Overview
This document provides step-by-step instructions for migrating authentication business logic from the deprecated Flask application files to the current FastAPI application (`fastapi-k8-proto`). The migration preserves only the business logic while adapting to FastAPI patterns and conventions.

## Source Files Analysis
- `depricated-auth-service.py` - Contains AuthService class with authentication business logic
- `depricated-user-model.py` - Contains User model with password handling
- `depricated-routes.py` - Contains auth endpoints (/auth/signup, /auth/login, /auth/me)
- `deprecated-auth-tests.py` - Contains comprehensive auth endpoint tests

## Target Architecture
The migrated auth system will follow FastAPI patterns:
- **Models**: SQLAlchemy models in `app/models/user.py`
- **Schemas**: Pydantic schemas in `app/schemas/auth.py`
- **Services**: Business logic in `app/services/auth_service.py`
- **Endpoints**: FastAPI routes in `app/api/endpoints/auth.py`
- **Dependencies**: Auth dependencies in `app/core/dependencies.py`
- **Tests**: Functional API tests in `tests/test_auth_endpoints.py`

---

## Step 1: Create User Model
**Goal**: Create a SQLAlchemy User model compatible with the current FastAPI application structure.

**Actions**:
1. Create `app/models/user.py` with User model
2. Update `app/models/__init__.py` to include User model
3. Create Alembic migration for users table

**Implementation**:

Create the User model following current patterns:
```python
# app/models/user.py
from sqlalchemy import Column, String, LargeBinary, Integer, DateTime
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from typing import Dict, Any

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, default="")
    password = Column(LargeBinary, nullable=False)  # Store bcrypt hash as bytes
    failed_attempts = Column(Integer, default=0, nullable=False)
    last_failed_attempt = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for serialization."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<User {self.email}>'
```

Update models init file:
```python
# app/models/__init__.py - Add User import
from app.models.user import User
# Add "User" to __all__ list
```

**Verification Strategy**:
- Run: `alembic revision --autogenerate -m "Add users table"`
- Run: `alembic upgrade head` (in Docker container)
- Verify table creation: Connect to database and check `users` table exists with correct schema

---

## Step 2: Create Auth Schemas
**Goal**: Create Pydantic schemas for authentication requests and responses.

**Actions**:
1. Create `app/schemas/auth.py` with auth-related schemas
2. Update `app/schemas/__init__.py` to include auth schemas

**Implementation**:

```python
# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re


class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    confirm_password: str = Field(..., min_length=8, max_length=72)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r"[A-Za-z]", v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError('Password must contain at least one special character')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SignupResponse(BaseModel):
    message: str
    user: UserResponse


class LoginResponse(BaseModel):
    message: str
    token: TokenResponse
    user: UserResponse
```

Update schemas init:
```python
# app/schemas/__init__.py - Add auth imports
from app.schemas.auth import (
    UserSignupRequest, UserLoginRequest, TokenResponse, 
    UserResponse, SignupResponse, LoginResponse
)
# Add to __all__ list
```

**Verification Strategy**:
- Import schemas in Python shell and verify they validate correctly
- Test password validation with various inputs
- Test email validation with invalid emails

---

## Step 3: Create Auth Service
**Goal**: Create authentication service with business logic adapted from Flask AuthService.

**Actions**:
1. Create `app/services/auth_service.py` with AuthService class
2. Install required dependencies (bcrypt, python-jose[cryptography])

**Implementation**:

```python
# app/services/auth_service.py
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
    SECRET_KEY = settings.SECRET_KEY  # Add to config
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
```

Add to config:
```python
# app/core/config.py - Add SECRET_KEY
SECRET_KEY: str = "your-secret-key-here"  # Should be from environment
```

**Verification Strategy**:
- Create test user in Python shell using AuthService.signup()
- Verify password hashing and verification work correctly
- Test JWT token creation and verification
- Check database for created user record

---

## Step 4: Create Auth Dependencies
**Goal**: Create FastAPI dependencies for authentication.

**Actions**:
1. Update `app/core/dependencies.py` with auth dependencies

**Implementation**:

```python
# app/core/dependencies.py - Add auth dependencies
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    auth_service = AuthService()
    return auth_service.get_current_user(credentials.credentials, db)

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to get current active user (can be extended with user status checks)."""
    return current_user
```

**Verification Strategy**:
- Test dependency injection in a simple endpoint
- Verify token extraction and user retrieval works

---

## Step 5: Create Auth Endpoints
**Goal**: Create FastAPI auth endpoints following current routing patterns.

**Actions**:
1. Create `app/api/endpoints/auth.py` with auth routes
2. Update `app/main.py` to include auth router

**Implementation**:

```python
# app/api/endpoints/auth.py
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
```

Update main.py:
```python
# app/main.py - Add auth router import and include
from app.api.endpoints import auth

# In create_application():
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
```

**Verification Strategy**:
- Start FastAPI server and check `/docs` for auth endpoints
- Test signup endpoint with valid data
- Test login endpoint with created user
- Test `/auth/me` endpoint with valid token

---

## Step 6: Install Dependencies
**Goal**: Install required Python packages for authentication.

**Actions**:
1. Add auth dependencies to requirements
2. Install packages in Docker container

**Implementation**:

Add to requirements file:
```
bcrypt>=4.0.1
python-jose[cryptography]>=3.3.0
python-multipart>=0.0.6
```

**Commands to run**:
```bash
# In Docker container
pip install bcrypt python-jose[cryptography] python-multipart
```

**Verification Strategy**:
- Import packages in Python shell to verify installation
- Check no import errors in auth service

---

## Step 7: Create Database Migration
**Goal**: Create and run Alembic migration for users table.

**Actions**:
1. Generate migration for User model
2. Run migration in Docker container
3. Verify table creation

**Commands to run**:
```bash
# In API Docker container
alembic revision --autogenerate -m "Add users table for authentication"
alembic upgrade head
```

**Verification Strategy**:
- Check migration file was created in `alembic/versions/`
- Connect to database and verify `users` table exists
- Check table schema matches User model definition
- Run: `SELECT * FROM users;` to verify table is accessible

---

## Step 8: Create Functional API Tests
**Goal**: Create comprehensive functional tests for auth endpoints.

**Actions**:
1. Create `tests/test_auth_endpoints.py` with API tests
2. Set up test database and fixtures

**Implementation**:

```python
# tests/test_auth_endpoints.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_db, Base
from app.models.user import User

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }

class TestAuthSignup:
    """Test auth signup endpoint."""
    
    def test_signup_success(self, client, test_user_data):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/signup", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "User registered successfully"
        assert "user" in data
        assert data["user"]["email"] == test_user_data["email"]
        
        # Verify user in database
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        assert user is not None
        db.close()

    def test_signup_missing_fields(self, client):
        """Test signup with missing fields."""
        response = client.post("/api/v1/auth/signup", json={
            "email": "test@example.com",
            "password": "SecurePass123!"
            # Missing confirm_password
        })
        assert response.status_code == 422

    def test_signup_password_mismatch(self, client, test_user_data):
        """Test signup with password mismatch."""
        test_user_data["confirm_password"] = "DifferentPass123!"
        response = client.post("/api/v1/auth/signup", json=test_user_data)
        assert response.status_code == 422

    def test_signup_weak_password(self, client):
        """Test signup with weak password."""
        response = client.post("/api/v1/auth/signup", json={
            "email": "test@example.com",
            "password": "weak",
            "confirm_password": "weak"
        })
        assert response.status_code == 422

    def test_signup_invalid_email(self, client):
        """Test signup with invalid email."""
        response = client.post("/api/v1/auth/signup", json={
            "email": "invalid-email",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        })
        assert response.status_code == 422

    def test_signup_duplicate_email(self, client, test_user_data):
        """Test signup with existing email."""
        # First signup
        client.post("/api/v1/auth/signup", json=test_user_data)
        
        # Second signup with same email
        response = client.post("/api/v1/auth/signup", json=test_user_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

class TestAuthLogin:
    """Test auth login endpoint."""
    
    def test_login_success(self, client, test_user_data):
        """Test successful login."""
        # First create user
        client.post("/api/v1/auth/signup", json=test_user_data)
        
        # Then login
        response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Login successful"
        assert "token" in data
        assert "access_token" in data["token"]
        assert data["token"]["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user_data):
        """Test login with wrong password."""
        # Create user
        client.post("/api/v1/auth/signup", json=test_user_data)
        
        # Login with wrong password
        response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123!"
        })
        assert response.status_code == 401

class TestAuthMe:
    """Test auth me endpoint."""
    
    def test_get_current_user_success(self, client, test_user_data):
        """Test getting current user info."""
        # Create and login user
        client.post("/api/v1/auth/signup", json=test_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["token"]["access_token"]
        
        # Get user info
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 403

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
```

**Commands to run**:
```bash
# In Docker container
pytest tests/test_auth_endpoints.py -v
```

**Verification Strategy**:
- All tests should pass
- Check test coverage includes all auth endpoints
- Verify database operations work correctly in tests

---

## Step 9: Integration Testing
**Goal**: Test complete auth flow end-to-end.

**Actions**:
1. Start FastAPI server
2. Test complete signup → login → authenticated request flow
3. Verify database state after operations

**Commands to run**:
```bash
# Start server
uvicorn app.main:app --reload

# Test endpoints with curl
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!","confirm_password":"SecurePass123!"}'

curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!"}'

# Use token from login response
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Verification Strategy**:
- Signup returns 201 with user data
- Login returns 200 with valid JWT token
- /auth/me returns user info when authenticated
- Check database has user record with hashed password
- Verify JWT token can be decoded and contains user_id

---

## Step 10: Update Existing Endpoints with Auth
**Goal**: Protect existing endpoints with authentication.

**Actions**:
1. Add auth dependency to protected endpoints
2. Update endpoint functions to use current_user
3. Test protected endpoints require authentication

**Implementation**:

Example for campaigns endpoint:
```python
# app/api/endpoints/campaigns.py - Add auth dependency
from app.core.dependencies import get_current_user
from app.models.user import User

@router.get("/", response_model=List[CampaignResponse])
async def get_campaigns(
    current_user: User = Depends(get_current_user),  # Add this
    db: Session = Depends(get_db)
):
    # Existing logic...
```

**Verification Strategy**:
- Test protected endpoints return 401 without token
- Test protected endpoints work with valid token
- Verify user context is available in endpoint handlers

---

## Step 11: Final Verification
**Goal**: Comprehensive testing of complete auth system.

**Actions**:
1. Run all tests
2. Test complete user flows
3. Verify security measures

**Commands to run**:
```bash
# Run all tests
pytest tests/ -v

# Test API documentation
curl http://localhost:8000/docs

# Test invalid scenarios
curl -X GET "http://localhost:8000/api/v1/campaigns" # Should return 401
curl -X GET "http://localhost:8000/api/v1/campaigns" -H "Authorization: Bearer invalid" # Should return 401
```

**Verification Strategy**:
- All tests pass
- API documentation shows auth endpoints
- Protected endpoints require authentication
- Invalid tokens are rejected
- Password hashing works correctly
- JWT tokens expire appropriately
- Email whitelist is enforced

---

## Security Considerations
1. **Password Storage**: Passwords are hashed with bcrypt
2. **JWT Security**: Tokens have expiration times
3. **Email Validation**: Proper email format validation
4. **Input Validation**: Pydantic schemas validate all inputs
5. **Error Handling**: No sensitive information in error messages
6. **Whitelist**: Email signup restrictions in place

## Post-Migration Cleanup
After successful migration and testing:
1. Remove deprecated files: `depricated-auth-service.py`, `depricated-user-model.py`, `deprecated-auth-tests.py`
2. Update documentation
3. Deploy to staging environment for further testing

## Rollback Plan
If migration fails:
1. Revert database migrations: `alembic downgrade -1`
2. Remove auth-related files
3. Restore from backup if necessary

---

This migration preserves all business logic from the original Flask auth system while adapting it to FastAPI patterns and conventions. Each step is discrete and testable, allowing for safe incremental migration. 