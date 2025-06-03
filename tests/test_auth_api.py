import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User
from tests.helpers.auth_helpers import AuthHelpers


class TestAuthSignup:
    """Test user signup functionality."""
    
    def test_signup_success(self, client, db_session):
        """Test successful user signup."""
        payload = {
            "email": "test@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!"
        }
        
        response = client.post("/api/v1/auth/signup", json=payload)
        
        # Verify API response
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "User registered successfully"
        assert data["user"]["email"] == payload["email"]
        assert "id" in data["user"]
        assert "password" not in data["user"]  # Password should not be returned
        
        # Verify user exists in database
        user = db_session.query(User).filter(User.email == payload["email"]).first()
        assert user is not None
        assert user.email == payload["email"]
        assert user.password is not None  # Password should be hashed
        
    def test_signup_email_whitelist_valid(self, client, db_session):
        """Test signup with whitelisted email."""
        payload = {
            "email": "test@hellacooltestingdomain.pizza",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!"
        }
        
        response = client.post("/api/v1/auth/signup", json=payload)
        assert response.status_code == 201
        
        # Verify user in database
        user = db_session.query(User).filter(User.email == payload["email"]).first()
        assert user is not None
    
    def test_signup_email_whitelist_invalid(self, client, db_session):
        """Test signup with non-whitelisted email fails."""
        payload = {
            "email": "invalid@notallowed.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!"
        }
        
        response = client.post("/api/v1/auth/signup", json=payload)
        assert response.status_code == 403
        
        # Verify no user created
        user = db_session.query(User).filter(User.email == payload["email"]).first()
        assert user is None
    
    def test_signup_duplicate_email(self, client, db_session):
        """Test signup with existing email fails."""
        # Create user first
        AuthHelpers.create_test_user(db_session, email="test@example.com")
        
        payload = {
            "email": "test@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!"
        }
        
        response = client.post("/api/v1/auth/signup", json=payload)
        assert response.status_code == 400
        
        # Verify only one user exists
        users = db_session.query(User).filter(User.email == payload["email"]).all()
        assert len(users) == 1
    
    def test_signup_password_mismatch(self, client, db_session):
        """Test signup with mismatched passwords fails."""
        payload = {
            "email": "test@example.com",
            "password": "TestPass123!",
            "confirm_password": "DifferentPass123!"
        }
        
        response = client.post("/api/v1/auth/signup", json=payload)
        assert response.status_code == 422  # Validation error
        
        # Verify no user created
        user = db_session.query(User).filter(User.email == payload["email"]).first()
        assert user is None
    
    def test_signup_weak_password(self, client, db_session):
        """Test signup with weak password fails."""
        payload = {
            "email": "test@example.com",
            "password": "weak",
            "confirm_password": "weak"
        }
        
        response = client.post("/api/v1/auth/signup", json=payload)
        assert response.status_code == 422  # Validation error
        
        # Verify no user created
        user = db_session.query(User).filter(User.email == payload["email"]).first()
        assert user is None


class TestAuthLogin:
    """Test user login functionality."""
    
    def test_login_success(self, client, db_session):
        """Test successful user login."""
        # Create user
        password = "TestPass123!"
        user = AuthHelpers.create_test_user(db_session, password=password)
        
        payload = {
            "email": user.email,
            "password": password
        }
        
        response = client.post("/api/v1/auth/login", json=payload)
        
        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Login successful"
        assert "token" in data
        assert data["token"]["token_type"] == "bearer"
        assert "access_token" in data["token"]
        assert data["user"]["email"] == user.email
        assert "password" not in data["user"]
    
    def test_login_invalid_email(self, client, db_session):
        """Test login with non-existent email fails."""
        payload = {
            "email": "nonexistent@example.com",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
    
    def test_login_invalid_password(self, client, db_session):
        """Test login with wrong password fails."""
        user = AuthHelpers.create_test_user(db_session)
        
        payload = {
            "email": user.email,
            "password": "WrongPassword123!"
        }
        
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
    
    def test_login_email_case_insensitive(self, client, db_session):
        """Test login is case insensitive for email."""
        password = "TestPass123!"
        user = AuthHelpers.create_test_user(db_session, email="test@example.com", password=password)
        
        payload = {
            "email": "TEST@EXAMPLE.COM",
            "password": password
        }
        
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200


class TestAuthProtectedEndpoints:
    """Test authentication for protected endpoints."""
    
    def test_get_current_user_success(self, client, db_session):
        """Test /auth/me endpoint with valid token."""
        user, token, headers = AuthHelpers.create_authenticated_user(db_session)
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
        assert data["id"] == user.id
        assert "password" not in data
    
    def test_get_current_user_no_token(self, client, db_session):
        """Test /auth/me endpoint without token fails."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client, db_session):
        """Test /auth/me endpoint with invalid token fails."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
    
    def test_protected_endpoint_requires_auth(self, client, db_session):
        """Test that protected endpoints require authentication."""
        # Test campaigns endpoint (should be protected)
        response = client.get("/api/v1/campaigns/")
        assert response.status_code == 401
    
    def test_protected_endpoint_with_auth(self, client, db_session):
        """Test that protected endpoints work with valid auth."""
        user, token, headers = AuthHelpers.create_authenticated_user(db_session)
        
        # Test campaigns endpoint with auth
        response = client.get("/api/v1/campaigns/", headers=headers)
        assert response.status_code == 200  # Should work with auth


class TestAuthSecurity:
    """Test authentication security measures."""
    
    def test_password_hashing(self, client, db_session):
        """Test that passwords are properly hashed."""
        password = "TestPass123!"
        user = AuthHelpers.create_test_user(db_session, password=password)
        
        # Verify password is hashed (not stored as plaintext)
        assert user.password != password.encode()
        assert len(user.password) > 20  # Bcrypt hashes are longer
        
        # Verify password verification works
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        assert auth_service.verify_password(password, user.password)
        assert not auth_service.verify_password("wrong_password", user.password) 