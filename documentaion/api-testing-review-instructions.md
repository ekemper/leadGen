# API Testing Review and Update Instructions

## Overview
This document provides comprehensive step-by-step instructions for an AI agent to review and update the API testing logic for the fastapi-k8-proto application. The application now has protected endpoints with JWT authentication, and all existing API tests need to be updated to handle authentication properly.

## Current State Analysis
- **Authentication System**: JWT-based authentication with middleware protection
- **Protected Endpoints**: All endpoints except `/api/v1/auth/*` and `/api/v1/health/*`
- **Existing Tests**: Functional API tests that hit endpoints and verify database state
- **Test Pattern**: Uses FastAPI TestClient with PostgreSQL test database
- **Missing**: Authentication handling in existing tests

## Prerequisites
- Docker container with API running
- PostgreSQL test database configured
- All dependencies installed (pytest, fastapi, sqlalchemy, etc.)

---

## Phase 1: Authentication Infrastructure Setup

### Step 1: Analyze Current Authentication System
**Goal**: Understand the complete authentication flow and dependencies.

**Actions**:
1. Read and analyze the authentication service (`app/services/auth_service.py`)
2. Review authentication middleware (`app/core/middleware.py`)
3. Examine auth endpoints (`app/api/endpoints/auth.py`)
4. Study auth schemas (`app/schemas/auth.py`)
5. Check user model (`app/models/user.py`)

**Verification Strategy**:
```bash
# Run in API container
python -c "
from app.services.auth_service import AuthService
from app.models.user import User
print('Auth service imported successfully')
print('User model imported successfully')
"
```

**Expected Output**: No import errors, successful module loading.

---

### Step 2: Create Authentication Test Helpers
**Goal**: Create reusable authentication utilities for tests.

**Actions**:
1. Create `tests/helpers/auth_helpers.py` with authentication utilities
2. Add user creation helpers
3. Add token generation helpers
4. Add authenticated client helpers

**Implementation**:
```python
# tests/helpers/auth_helpers.py
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
    def create_authenticated_user(db: Session) -> tuple[User, str, Dict[str, str]]:
        """Create a user and return user, token, and headers."""
        user = AuthHelpers.create_test_user(db)
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
```

**Verification Strategy**:
```bash
# Run in API container
python -c "
from tests.helpers.auth_helpers import AuthHelpers
print('AuthHelpers imported successfully')
"
```

**Expected Output**: No import errors.

---

### Step 3: Update Test Configuration for Authentication
**Goal**: Update `conftest.py` to include authentication fixtures.

**Actions**:
1. Add authentication helper fixtures to `tests/conftest.py`
2. Add user cleanup to database cleanup
3. Create authenticated client fixtures

**Implementation**:
```python
# Add to tests/conftest.py

from tests.helpers.auth_helpers import AuthHelpers

@pytest.fixture
def auth_helpers(db_session):
    """Provide authentication helper utilities for tests."""
    return AuthHelpers

@pytest.fixture
def test_user(db_session):
    """Create a test user for authentication."""
    return AuthHelpers.create_test_user(db_session)

@pytest.fixture
def authenticated_user(db_session):
    """Create a user and return user, token, and headers."""
    return AuthHelpers.create_authenticated_user(db_session)

@pytest.fixture
def authenticated_client(client, db_session):
    """Create an authenticated client with user, token, and headers."""
    user, token, headers = AuthHelpers.get_authenticated_client_data(client, db_session)
    
    # Create a wrapper that automatically includes auth headers
    class AuthenticatedClient:
        def __init__(self, client, headers, user, token):
            self.client = client
            self.headers = headers
            self.user = user
            self.token = token
        
        def get(self, url, **kwargs):
            kwargs.setdefault('headers', {}).update(self.headers)
            return self.client.get(url, **kwargs)
        
        def post(self, url, **kwargs):
            kwargs.setdefault('headers', {}).update(self.headers)
            return self.client.post(url, **kwargs)
        
        def patch(self, url, **kwargs):
            kwargs.setdefault('headers', {}).update(self.headers)
            return self.client.patch(url, **kwargs)
        
        def delete(self, url, **kwargs):
            kwargs.setdefault('headers', {}).update(self.headers)
            return self.client.delete(url, **kwargs)
    
    return AuthenticatedClient(client, headers, user, token)

# Update cleanup_database fixture to include users
@pytest.fixture(autouse=True)
def cleanup_database():
    """Clean up database before each test."""
    # Import models to ensure they're registered
    from app.models.campaign import Campaign
    from app.models.job import Job
    from app.models.organization import Organization
    from app.models.user import User
    
    # Clean before test
    db = TestingSessionLocal()
    try:
        # Delete in correct order to respect foreign keys
        db.query(Job).delete()
        db.query(Campaign).delete()
        db.query(Organization).delete()
        db.query(User).delete()  # Add user cleanup
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    
    yield
    
    # Clean after test (backup cleanup)
    db = TestingSessionLocal()
    try:
        db.query(Job).delete()
        db.query(Campaign).delete()
        db.query(Organization).delete()
        db.query(User).delete()  # Add user cleanup
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
```

**Verification Strategy**:
```bash
# Run in API container
cd /app && python -m pytest tests/conftest.py::test_fixtures -v
```

**Expected Output**: All fixtures load without errors.

---

## Phase 2: Authentication Endpoint Testing

### Step 4: Create Comprehensive Auth API Tests
**Goal**: Create complete test suite for authentication endpoints.

**Actions**:
1. Create `tests/test_auth_api.py` with comprehensive auth tests
2. Test signup, login, and protected endpoint access
3. Test authentication edge cases and security

**Implementation**:
```python
# tests/test_auth_api.py
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
    
    def test_token_expiration(self, client, db_session):
        """Test that expired tokens are rejected."""
        # This would require mocking time or creating expired tokens
        # Implementation depends on how you want to handle time in tests
        pass
    
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
```

**Verification Strategy**:
```bash
# Run in API container
cd /app && python -m pytest tests/test_auth_api.py -v
```

**Expected Output**: All authentication tests pass.

---

## Phase 3: Update Existing API Tests

### Step 5: Update Campaign API Tests
**Goal**: Update existing campaign tests to handle authentication.

**Actions**:
1. Modify `tests/test_campaigns_api.py` to use authentication
2. Replace `client` fixture with `authenticated_client` where needed
3. Update test assertions to account for user context

**Implementation Strategy**:
```python
# Update tests/test_campaigns_api.py

# Add authentication imports at top
from tests.helpers.auth_helpers import AuthHelpers

# Update fixtures to use authentication
@pytest.fixture
def authenticated_campaign_payload(authenticated_client, organization_payload):
    """Return a valid payload for creating a campaign via the API with auth."""
    # Create an organization first using authenticated client
    response = authenticated_client.post("/api/v1/organizations/", json=organization_payload)
    assert response.status_code == 201
    org_id = response.json()["id"]
    
    return {
        "name": "API Test Campaign",
        "description": "This campaign is created by tests",
        "fileName": "input-file.csv",
        "totalRecords": 25,
        "url": "https://app.apollo.io/#/some-search",
        "organization_id": org_id
    }

# Update test functions to use authenticated_client
def test_create_campaign_success(authenticated_client, db_session, authenticated_campaign_payload):
    """Test successful campaign creation with all required fields."""
    response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    
    # Rest of test remains the same...
    assert response.status_code == 201
    # ... existing assertions

# Add authentication-specific tests
def test_create_campaign_requires_auth(client, db_session, campaign_payload):
    """Test that campaign creation requires authentication."""
    response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert response.status_code == 401

def test_list_campaigns_requires_auth(client, db_session):
    """Test that listing campaigns requires authentication."""
    response = client.get("/api/v1/campaigns/")
    assert response.status_code == 401
```

**Verification Strategy**:
```bash
# Run in API container
cd /app && python -m pytest tests/test_campaigns_api.py::test_create_campaign_success -v
cd /app && python -m pytest tests/test_campaigns_api.py::test_create_campaign_requires_auth -v
```

**Expected Output**: Tests pass with authentication working correctly.

---

### Step 6: Update Organization API Tests
**Goal**: Update organization tests for authentication.

**Actions**:
1. Modify `tests/test_organizations_api.py` to use authentication
2. Add authentication requirement tests
3. Update all test functions to use `authenticated_client`

**Implementation Strategy**:
```python
# Similar pattern as campaigns - update all test functions
# to use authenticated_client instead of client

def test_create_organization_success(authenticated_client, db_session, organization_payload):
    """Test successful organization creation."""
    response = authenticated_client.post("/api/v1/organizations/", json=organization_payload)
    # ... rest of test

def test_create_organization_requires_auth(client, db_session, organization_payload):
    """Test that organization creation requires authentication."""
    response = client.post("/api/v1/organizations/", json=organization_payload)
    assert response.status_code == 401
```

**Verification Strategy**:
```bash
# Run in API container
cd /app && python -m pytest tests/test_organizations_api.py -v
```

**Expected Output**: All organization tests pass with authentication.

---

### Step 7: Update Leads API Tests
**Goal**: Update leads tests for authentication.

**Actions**:
1. Modify `tests/test_leads_api.py` to use authentication
2. Follow same pattern as other endpoint tests

**Verification Strategy**:
```bash
# Run in API container
cd /app && python -m pytest tests/test_leads_api.py -v
```

**Expected Output**: All leads tests pass with authentication.

---

### Step 8: Update Integration Tests
**Goal**: Update integration tests to handle authentication.

**Actions**:
1. Update `tests/test_organization_campaign_integration.py`
2. Update `tests/test_helpers_integration.py`
3. Ensure all integration tests use authenticated clients

**Verification Strategy**:
```bash
# Run in API container
cd /app && python -m pytest tests/test_organization_campaign_integration.py -v
cd /app && python -m pytest tests/test_helpers_integration.py -v
```

**Expected Output**: All integration tests pass.

---

## Phase 4: Comprehensive Testing and Validation

### Step 9: Create API Security Tests
**Goal**: Create comprehensive security tests for the API.

**Actions**:
1. Create `tests/test_api_security.py`
2. Test authentication bypass attempts
3. Test authorization edge cases
4. Test token manipulation

**Implementation**:
```python
# tests/test_api_security.py
import pytest
import jwt
from datetime import datetime, timedelta

from tests.helpers.auth_helpers import AuthHelpers


class TestAPISecurityAuthentication:
    """Test API security around authentication."""
    
    def test_all_protected_endpoints_require_auth(self, client):
        """Test that all protected endpoints require authentication."""
        protected_endpoints = [
            ("GET", "/api/v1/campaigns/"),
            ("POST", "/api/v1/campaigns/"),
            ("GET", "/api/v1/organizations/"),
            ("POST", "/api/v1/organizations/"),
            ("GET", "/api/v1/leads/"),
            ("POST", "/api/v1/leads/"),
            ("GET", "/api/v1/jobs/"),
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            
            assert response.status_code == 401, f"{method} {endpoint} should require auth"
    
    def test_public_endpoints_no_auth_required(self, client):
        """Test that public endpoints don't require authentication."""
        public_endpoints = [
            ("GET", "/api/v1/health"),
            ("POST", "/api/v1/auth/signup"),
            ("POST", "/api/v1/auth/login"),
        ]
        
        for method, endpoint in public_endpoints:
            if method == "GET":
                response = client.get(endpoint)
                # Health should return 200, others may vary
                assert response.status_code != 401, f"{method} {endpoint} should not require auth"
    
    def test_malformed_token_rejected(self, client):
        """Test that malformed tokens are rejected."""
        malformed_tokens = [
            "not_a_token",
            "Bearer",
            "Bearer ",
            "Bearer invalid.token.here",
            "Basic dGVzdDp0ZXN0",  # Basic auth instead of Bearer
        ]
        
        for token in malformed_tokens:
            headers = {"Authorization": token}
            response = client.get("/api/v1/campaigns/", headers=headers)
            assert response.status_code == 401, f"Token '{token}' should be rejected"
    
    def test_expired_token_rejected(self, client, db_session):
        """Test that expired tokens are rejected."""
        user = AuthHelpers.create_test_user(db_session)
        
        # Create expired token
        from app.services.auth_service import AuthService
        expired_payload = {
            "user_id": user.id,
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        expired_token = jwt.encode(expired_payload, AuthService.SECRET_KEY, algorithm=AuthService.ALGORITHM)
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/campaigns/", headers=headers)
        assert response.status_code == 401
    
    def test_token_with_invalid_user_rejected(self, client, db_session):
        """Test that tokens with non-existent user IDs are rejected."""
        from app.services.auth_service import AuthService
        
        # Create token with non-existent user ID
        fake_payload = {
            "user_id": "non-existent-user-id",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        fake_token = jwt.encode(fake_payload, AuthService.SECRET_KEY, algorithm=AuthService.ALGORITHM)
        
        headers = {"Authorization": f"Bearer {fake_token}"}
        response = client.get("/api/v1/campaigns/", headers=headers)
        assert response.status_code == 401


class TestAPISecurityAuthorization:
    """Test API security around authorization."""
    
    def test_user_can_only_access_own_data(self, client, db_session):
        """Test that users can only access their own data."""
        # This test would be implemented once user-scoped data is implemented
        # For now, document the requirement
        pass
    
    def test_sql_injection_prevention(self, authenticated_client, db_session):
        """Test that SQL injection attempts are prevented."""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1; DELETE FROM campaigns; --",
            "' UNION SELECT * FROM users --",
        ]
        
        for payload in sql_injection_payloads:
            # Test in campaign name
            response = authenticated_client.post("/api/v1/campaigns/", json={
                "name": payload,
                "description": "Test",
                "fileName": "test.csv",
                "totalRecords": 1,
                "url": "https://example.com",
                "organization_id": "test-org-id"
            })
            # Should either succeed (payload treated as string) or fail validation
            # Should NOT cause database errors
            assert response.status_code in [201, 400, 422], f"SQL injection payload caused unexpected error: {payload}"
    
    def test_xss_prevention_in_responses(self, authenticated_client, db_session):
        """Test that XSS payloads in responses are handled safely."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
        ]
        
        for payload in xss_payloads:
            # Create organization with XSS payload
            response = authenticated_client.post("/api/v1/organizations/", json={
                "name": payload,
                "description": "Test organization"
            })
            
            if response.status_code == 201:
                # Verify the payload is returned as-is (not executed)
                data = response.json()
                assert data["name"] == payload, "XSS payload should be stored and returned as string"
```

**Verification Strategy**:
```bash
# Run in API container
cd /app && python -m pytest tests/test_api_security.py -v
```

**Expected Output**: All security tests pass, confirming proper authentication and authorization.

---

### Step 10: Run Complete Test Suite
**Goal**: Verify all tests pass with authentication implemented.

**Actions**:
1. Run all API tests
2. Verify database state after tests
3. Check for any authentication-related failures

**Commands**:
```bash
# Run in API container
cd /app

# Run all API tests
python -m pytest tests/test_*_api.py -v

# Run integration tests
python -m pytest tests/test_*_integration.py -v

# Run security tests
python -m pytest tests/test_api_security.py -v

# Run all tests
python -m pytest tests/ -v --tb=short

# Check test coverage
python -m pytest tests/ --cov=app --cov-report=html
```

**Verification Strategy**:
- All tests should pass
- No authentication-related failures
- Coverage report should show good coverage of auth code
- Database should be clean after tests

**Expected Output**: 
```
========================= test session starts =========================
collected X items

tests/test_auth_api.py::TestAuthSignup::test_signup_success PASSED
tests/test_auth_api.py::TestAuthLogin::test_login_success PASSED
tests/test_campaigns_api.py::test_create_campaign_success PASSED
tests/test_organizations_api.py::test_create_organization_success PASSED
...
========================= X passed in Y.YYs =========================
```

---

## Phase 5: Performance and Load Testing

### Step 11: Create API Performance Tests
**Goal**: Test API performance with authentication overhead.

**Actions**:
1. Create `tests/test_api_performance.py`
2. Test authentication performance
3. Test concurrent authenticated requests

**Implementation**:
```python
# tests/test_api_performance.py
import pytest
import time
import concurrent.futures
from threading import Thread

from tests.helpers.auth_helpers import AuthHelpers


class TestAPIPerformance:
    """Test API performance with authentication."""
    
    def test_authentication_performance(self, client, db_session):
        """Test authentication doesn't add significant overhead."""
        # Create user
        user, token, headers = AuthHelpers.create_authenticated_user(db_session)
        
        # Time authenticated requests
        start_time = time.time()
        for _ in range(10):
            response = client.get("/api/v1/campaigns/", headers=headers)
            assert response.status_code == 200
        auth_time = time.time() - start_time
        
        # Authentication should not add more than 100ms per request on average
        avg_time_per_request = auth_time / 10
        assert avg_time_per_request < 0.1, f"Authentication too slow: {avg_time_per_request}s per request"
    
    def test_concurrent_authenticated_requests(self, client, db_session):
        """Test concurrent authenticated requests work correctly."""
        # Create multiple users
        users_data = []
        for i in range(5):
            user, token, headers = AuthHelpers.create_authenticated_user(db_session, email=f"user{i}@example.com")
            users_data.append((user, token, headers))
        
        def make_request(headers):
            response = client.get("/api/v1/campaigns/", headers=headers)
            return response.status_code
        
        # Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, headers) for _, _, headers in users_data]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(status == 200 for status in results), "Some concurrent requests failed"
    
    def test_token_validation_performance(self, client, db_session):
        """Test token validation performance."""
        user, token, headers = AuthHelpers.create_authenticated_user(db_session)
        
        # Time token validation
        start_time = time.time()
        for _ in range(100):
            response = client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 200
        validation_time = time.time() - start_time
        
        # Token validation should be fast
        avg_time = validation_time / 100
        assert avg_time < 0.05, f"Token validation too slow: {avg_time}s per validation"
```

**Verification Strategy**:
```bash
# Run in API container
cd /app && python -m pytest tests/test_api_performance.py -v
```

**Expected Output**: Performance tests pass, confirming authentication doesn't significantly impact performance.

---

## Phase 6: Documentation and Final Validation

### Step 12: Update Test Documentation
**Goal**: Document the updated testing approach and patterns.

**Actions**:
1. Update test README files
2. Document authentication testing patterns
3. Create testing guidelines

**Implementation**:
```markdown
# tests/README.md

# API Testing Guide

## Authentication in Tests

All API tests now require authentication. Use these patterns:

### Basic Authentication Test Pattern
```python
def test_endpoint_with_auth(authenticated_client, db_session):
    response = authenticated_client.get("/api/v1/endpoint/")
    assert response.status_code == 200
```

### Manual Authentication Pattern
```python
def test_endpoint_manual_auth(client, db_session):
    user, token, headers = AuthHelpers.create_authenticated_user(db_session)
    response = client.get("/api/v1/endpoint/", headers=headers)
    assert response.status_code == 200
```

### Testing Authentication Requirements
```python
def test_endpoint_requires_auth(client):
    response = client.get("/api/v1/endpoint/")
    assert response.status_code == 401
```

## Available Fixtures

- `authenticated_client`: Pre-authenticated client with user and token
- `test_user`: Basic test user in database
- `authenticated_user`: Returns (user, token, headers) tuple
- `auth_helpers`: AuthHelpers class instance

## Test Database

Tests use a separate PostgreSQL database that is cleaned between tests.
User data is automatically cleaned up.
```

**Verification Strategy**:
- Documentation is clear and accurate
- Examples work when copied

---

### Step 13: Final Integration Test
**Goal**: Run complete end-to-end test of the entire API with authentication.

**Actions**:
1. Create comprehensive integration test
2. Test complete user workflows
3. Verify all systems work together

**Implementation**:
```python
# tests/test_complete_api_integration.py
import pytest

from tests.helpers.auth_helpers import AuthHelpers


def test_complete_user_workflow(client, db_session):
    """Test complete user workflow from signup to using protected endpoints."""
    
    # 1. User signs up
    signup_response = client.post("/api/v1/auth/signup", json={
        "email": "integration@example.com",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!"
    })
    assert signup_response.status_code == 201
    
    # 2. User logs in
    login_response = client.post("/api/v1/auth/login", json={
        "email": "integration@example.com",
        "password": "TestPass123!"
    })
    assert login_response.status_code == 200
    token = login_response.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. User accesses protected endpoint
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "integration@example.com"
    
    # 4. User creates organization
    org_response = client.post("/api/v1/organizations/", 
        headers=headers,
        json={
            "name": "Integration Test Org",
            "description": "Created during integration test"
        }
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]
    
    # 5. User creates campaign
    campaign_response = client.post("/api/v1/campaigns/",
        headers=headers,
        json={
            "name": "Integration Test Campaign",
            "description": "Created during integration test",
            "fileName": "test.csv",
            "totalRecords": 10,
            "url": "https://example.com",
            "organization_id": org_id
        }
    )
    assert campaign_response.status_code == 201
    campaign_id = campaign_response.json()["id"]
    
    # 6. User lists campaigns
    campaigns_response = client.get("/api/v1/campaigns/", headers=headers)
    assert campaigns_response.status_code == 200
    campaigns = campaigns_response.json()
    assert len(campaigns) == 1
    assert campaigns[0]["id"] == campaign_id
    
    # 7. Verify database state
    from app.models.user import User
    from app.models.organization import Organization
    from app.models.campaign import Campaign
    
    user = db_session.query(User).filter(User.email == "integration@example.com").first()
    assert user is not None
    
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    assert org is not None
    assert org.name == "Integration Test Org"
    
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert campaign is not None
    assert campaign.name == "Integration Test Campaign"
    assert campaign.organization_id == org_id


def test_authentication_edge_cases(client, db_session):
    """Test various authentication edge cases."""
    
    # Test accessing protected endpoint without auth
    response = client.get("/api/v1/campaigns/")
    assert response.status_code == 401
    
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/v1/campaigns/", headers=headers)
    assert response.status_code == 401
    
    # Test with malformed auth header
    headers = {"Authorization": "invalid_format"}
    response = client.get("/api/v1/campaigns/", headers=headers)
    assert response.status_code == 401
    
    # Test public endpoints still work
    response = client.get("/api/v1/health")
    assert response.status_code == 200
```

**Verification Strategy**:
```bash
# Run in API container
cd /app && python -m pytest tests/test_complete_api_integration.py -v
```

**Expected Output**: Complete integration test passes, confirming entire system works end-to-end.

---

### Step 14: Final Test Suite Execution
**Goal**: Run complete test suite and generate final report.

**Commands**:
```bash
# Run in API container
cd /app

# Clean test database
python -c "
from tests.conftest import TestingSessionLocal, engine
from app.core.database import Base
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print('Test database reset')
"

# Run complete test suite with coverage
python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# Run only API tests
python -m pytest tests/test_*_api.py tests/test_*_integration.py -v

# Generate test report
python -m pytest tests/ --html=test_report.html --self-contained-html
```

**Verification Strategy**:
- All tests pass (100% success rate)
- Coverage report shows good coverage of authentication code
- No authentication-related failures
- Test report shows comprehensive test execution

**Expected Final Output**:
```
========================= test session starts =========================
collected XX items

tests/test_auth_api.py::TestAuthSignup::test_signup_success PASSED
tests/test_auth_api.py::TestAuthLogin::test_login_success PASSED
tests/test_campaigns_api.py::test_create_campaign_success PASSED
tests/test_organizations_api.py::test_create_organization_success PASSED
tests/test_api_security.py::TestAPISecurityAuthentication::test_all_protected_endpoints_require_auth PASSED
tests/test_complete_api_integration.py::test_complete_user_workflow PASSED
...

========================= XX passed in Y.YYs =========================

Coverage Report:
app/services/auth_service.py    95%
app/api/endpoints/auth.py       100%
app/core/dependencies.py        90%
app/core/middleware.py          85%
...
```

---

## Success Criteria

### Functional Requirements ✅
- [ ] All existing API tests updated to handle authentication
- [ ] New authentication-specific tests created
- [ ] All protected endpoints require valid JWT tokens
- [ ] Public endpoints (auth, health) remain accessible
- [ ] User signup, login, and token validation work correctly

### Security Requirements ✅
- [ ] Authentication bypass attempts fail
- [ ] Malformed tokens are rejected
- [ ] Expired tokens are rejected
- [ ] SQL injection prevention verified
- [ ] XSS prevention verified

### Performance Requirements ✅
- [ ] Authentication adds minimal overhead (<100ms per request)
- [ ] Concurrent authenticated requests work correctly
- [ ] Token validation is performant (<50ms per validation)

### Testing Requirements ✅
- [ ] 100% test pass rate
- [ ] Good test coverage of authentication code (>90%)
- [ ] Integration tests verify end-to-end workflows
- [ ] Database cleanup works correctly
- [ ] Test documentation is updated

### Code Quality Requirements ✅
- [ ] Consistent patterns across all test files
- [ ] Reusable authentication helpers
- [ ] Clear test organization and naming
- [ ] Proper error handling in tests
- [ ] No deprecated or conflicting patterns

---

## Troubleshooting Guide

### Common Issues and Solutions

1. **Tests failing with 401 errors**
   - Check that `authenticated_client` fixture is being used
   - Verify token generation is working
   - Check middleware configuration

2. **Database cleanup issues**
   - Verify User model is included in cleanup
   - Check foreign key constraints
   - Ensure proper transaction handling

3. **Token validation failures**
   - Check SECRET_KEY configuration
   - Verify JWT library versions
   - Check token expiration settings

4. **Performance issues**
   - Profile authentication middleware
   - Check database connection pooling
   - Verify test database performance

5. **Import errors**
   - Check Python path configuration
   - Verify all dependencies installed
   - Check circular import issues

---

## Maintenance Notes

### Regular Maintenance Tasks
1. Update authentication tests when adding new endpoints
2. Review security tests quarterly
3. Update performance benchmarks as system grows
4. Keep authentication patterns consistent across tests

### Future Enhancements
1. Add user role-based testing when roles are implemented
2. Add API rate limiting tests
3. Add multi-tenant testing when implemented
4. Add OAuth/SSO testing if implemented

---

This completes the comprehensive API testing review and update instructions. The AI agent should follow these steps sequentially, verifying each step before proceeding to the next. 