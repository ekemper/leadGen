import uuid
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.auth_service import AuthService


class AuthHelpers:
    """Helper utilities for authentication in tests."""
    
    @staticmethod
    def create_test_user(
        db: Session, 
        email: str = "test@example.com",
        password: str = "TestPass123!",
        name: str = "Test User"
    ) -> User:
        """Create a test user in the database."""
        auth_service = AuthService()
        hashed_password = auth_service.hash_password(password)
        
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            password=hashed_password,
            name=name
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def create_access_token(user: User) -> str:
        """Create an access token for a user."""
        auth_service = AuthService()
        return auth_service.create_access_token(data={"user_id": user.id})
    
    @staticmethod
    def get_auth_headers(token: str) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        return {"Authorization": f"Bearer {token}"}
    
    @staticmethod
    def create_authenticated_user(db: Session, email: str = "test@hellacooltestingdomain.pizza") -> tuple[User, str, Dict[str, str]]:
        """Create a user and return user, token, and headers."""
        user = AuthHelpers.create_test_user(db, email=email)
        token = AuthHelpers.create_access_token(user)
        headers = AuthHelpers.get_auth_headers(token)
        return user, token, headers
    
    @staticmethod
    def signup_user(client: TestClient, email: str = "test@example.com", password: str = "TestPass123!") -> Dict[str, Any]:
        """Sign up a user via API and return response data."""
        response = client.post("/api/v1/auth/signup", json={
            "email": email,
            "password": password,
            "confirm_password": password
        })
        assert response.status_code == 201
        return response.json()
    
    @staticmethod
    def login_user(client: TestClient, email: str = "test@example.com", password: str = "TestPass123!") -> Dict[str, Any]:
        """Login a user via API and return response data."""
        response = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 200
        return response.json()
    
    @staticmethod
    def get_authenticated_client_data(client: TestClient, db: Session) -> tuple[User, str, Dict[str, str]]:
        """Create user via API and return authentication data."""
        # Create user via signup
        signup_data = AuthHelpers.signup_user(client)
        
        # Login to get token
        login_data = AuthHelpers.login_user(client)
        token = login_data["token"]["access_token"]
        headers = AuthHelpers.get_auth_headers(token)
        
        # Get user from database
        user = db.query(User).filter(User.email == signup_data["user"]["email"]).first()
        
        return user, token, headers 