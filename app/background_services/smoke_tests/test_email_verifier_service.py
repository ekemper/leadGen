"""
Tests for EmailVerifierService with Rate Limiting Integration

This test suite validates the EmailVerifierService functionality including:
- Backward compatibility for existing usage patterns
- Rate limiting integration and behavior
- Error handling and graceful degradation
- API response handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from app.background_services.email_verifier_service import EmailVerifierService
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter

class TestEmailVerifierService:
    """Test suite for EmailVerifierService."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Mock the environment variable
        self.api_key_patcher = patch.dict('os.environ', {'MILLIONVERIFIER_API_KEY': 'test-api-key'})
        self.api_key_patcher.start()
        
    def teardown_method(self):
        """Cleanup after each test method."""
        self.api_key_patcher.stop()

    def test_backward_compatibility_initialization(self):
        """Test that EmailVerifierService can be initialized without rate limiter (backward compatibility)."""
        service = EmailVerifierService()
        
        assert service.api_key == 'test-api-key'
        assert service.base_url == "https://api.millionverifier.com/api/v3/"
        assert service.max_retries == 3
        assert service.retry_delay == 1
        assert service.rate_limiter is None
        
    def test_rate_limiter_initialization(self):
        """Test that EmailVerifierService can be initialized with rate limiter."""
        mock_redis = Mock()
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'MillionVerifier', 60, 60)
        
        service = EmailVerifierService(rate_limiter=rate_limiter)
        
        assert service.rate_limiter is rate_limiter
        assert service.api_key == 'test-api-key'
        
    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="MILLIONVERIFIER_API_KEY environment variable is not set"):
                EmailVerifierService()

    @patch('requests.get')
    def test_verify_email_success_without_rate_limiter(self, mock_get):
        """Test successful email verification without rate limiter."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'email': 'test@example.com',
            'result': 'deliverable',
            'score': 99
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test
        service = EmailVerifierService()
        result = service.verify_email('test@example.com')
        
        # Verify
        assert result['email'] == 'test@example.com'
        assert result['result'] == 'deliverable'
        assert result['score'] == 99
        mock_get.assert_called_once_with(
            "https://api.millionverifier.com/api/v3/?api=test-api-key&email=test@example.com"
        )

    @patch('requests.get')
    def test_verify_email_success_with_rate_limiter(self, mock_get):
        """Test successful email verification with rate limiter."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'email': 'test@example.com',
            'result': 'deliverable',
            'score': 99
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Setup mock rate limiter
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.execute.return_value = [1, True]
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'MillionVerifier', 60, 60)
        
        # Test
        service = EmailVerifierService(rate_limiter=rate_limiter)
        result = service.verify_email('test@example.com')
        
        # Verify
        assert result['email'] == 'test@example.com'
        assert result['result'] == 'deliverable'
        mock_get.assert_called_once()

    def test_verify_email_rate_limit_exceeded(self):
        """Test email verification when rate limit is exceeded."""
        # Setup mock rate limiter that denies requests
        mock_redis = Mock()
        mock_redis.get.return_value = '60'  # At limit
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.incr.return_value = 61  # Exceeds limit
        mock_redis.execute.return_value = [61, True]
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'MillionVerifier', 60, 60)
        
        # Test
        service = EmailVerifierService(rate_limiter=rate_limiter)
        result = service.verify_email('test@example.com')
        
        # Verify rate limit response
        assert result['status'] == 'rate_limited'
        assert 'Rate limit exceeded' in result['error']
        assert 'remaining_requests' in result
        assert result['retry_after_seconds'] == 60

    @patch('requests.get')
    def test_verify_email_api_error(self, mock_get):
        """Test email verification with API error."""
        # Setup mock to raise exception
        mock_get.side_effect = requests.RequestException("API Error")
        
        # Test
        service = EmailVerifierService()
        result = service.verify_email('test@example.com')
        
        # Verify error response
        assert result['status'] == 'error'
        assert 'API Error' in result['error']

    def test_verify_email_rate_limiter_failure_graceful_degradation(self):
        """Test that rate limiter failures don't prevent email verification."""
        # Setup mock rate limiter that fails
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis connection failed")
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'MillionVerifier', 60, 60)
        
        with patch('requests.get') as mock_get:
            # Setup successful API response
            mock_response = Mock()
            mock_response.json.return_value = {'email': 'test@example.com', 'result': 'deliverable'}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Test
            service = EmailVerifierService(rate_limiter=rate_limiter)
            result = service.verify_email('test@example.com')
            
            # Verify that API call still succeeded despite rate limiter failure
            assert result['email'] == 'test@example.com'
            assert result['result'] == 'deliverable'
            mock_get.assert_called_once()

    def test_verify_email_with_mock_redis_integration(self):
        """Integration test with mock Redis for rate limiting behavior."""
        # Setup mock Redis that allows first request, denies second
        mock_redis = Mock()
        call_count = 0
        
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [1, True]  # First call succeeds
            else:
                return [2, True]  # Second call exceeds limit of 1
                
        mock_redis.get.return_value = None
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.execute.side_effect = mock_execute
        
        # Create rate limiter with limit of 1 request
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'MillionVerifier', 1, 60)
        service = EmailVerifierService(rate_limiter=rate_limiter)
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {'result': 'deliverable'}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # First call should succeed
            result1 = service.verify_email('test1@example.com')
            assert result1['result'] == 'deliverable'
            
            # Second call should be rate limited
            result2 = service.verify_email('test2@example.com')
            assert result2['status'] == 'rate_limited'

# Integration tests that could be run with actual Redis (when available)
class TestEmailVerifierServiceIntegration:
    """Integration tests for EmailVerifierService (require Redis)."""
    
    @pytest.mark.skip(reason="Requires Redis connection and API key")
    def test_real_rate_limiter_integration(self):
        """Test with real Redis connection (skipped by default)."""
        # This test would require actual Redis and API setup
        # Uncomment and configure when running integration tests
        pass

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"]) 