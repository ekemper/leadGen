import pytest
from jose import jwt
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
            elif method == "POST":
                # These will fail validation but shouldn't require auth
                response = client.post(endpoint, json={})
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
                # Verify the payload is either stored as-is or sanitized (both are acceptable)
                data = response.json()
                returned_name = data["name"]
                
                # The API may sanitize XSS content, which is good security practice
                # We just verify that dangerous scripts are not executable
                assert "<script>" not in returned_name or "alert(&#x27;XSS&#x27;)" in returned_name, \
                    f"XSS payload should be sanitized or stored safely, got: {returned_name}"


class TestAPISecurityPerformance:
    """Test API security performance measures."""
    
    def test_authentication_performance(self, client, db_session):
        """Test authentication doesn't add significant overhead."""
        # Create user
        user, token, headers = AuthHelpers.create_authenticated_user(db_session)
        
        # Time authenticated requests
        import time
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
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, headers) for _, _, headers in users_data]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(status == 200 for status in results), "Some concurrent requests failed"
    
    def test_token_validation_performance(self, client, db_session):
        """Test token validation performance."""
        user, token, headers = AuthHelpers.create_authenticated_user(db_session)
        
        # Time token validation
        import time
        start_time = time.time()
        for _ in range(100):
            response = client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 200
        validation_time = time.time() - start_time
        
        # Token validation should be fast
        avg_time = validation_time / 100
        assert avg_time < 0.05, f"Token validation too slow: {avg_time}s per validation" 