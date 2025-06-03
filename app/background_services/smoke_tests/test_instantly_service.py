"""
Tests for InstantlyService with Rate Limiting Integration

This test suite validates the InstantlyService functionality including:
- Backward compatibility for existing usage patterns
- Rate limiting integration and behavior
- Error handling and graceful degradation
- API response handling for all methods (create_lead, create_campaign, get_campaign_analytics_overview)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from app.background_services.instantly_service import InstantlyService
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter

class TestInstantlyService:
    """Test suite for InstantlyService."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Mock the environment variable
        self.api_key_patcher = patch.dict('os.environ', {'INSTANTLY_API_KEY': 'test-api-key'})
        self.api_key_patcher.start()
        
    def teardown_method(self):
        """Cleanup after each test method."""
        self.api_key_patcher.stop()

    def test_backward_compatibility_initialization(self):
        """Test that InstantlyService can be initialized without rate limiter (backward compatibility)."""
        service = InstantlyService()
        
        assert service.api_key == 'test-api-key'
        assert service.headers == {
            "Authorization": "Bearer test-api-key",
            "Content-Type": "application/json"
        }
        assert service.rate_limiter is None
        
    def test_rate_limiter_initialization(self):
        """Test that InstantlyService can be initialized with rate limiter."""
        mock_redis = Mock()
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Instantly', 100, 60)
        
        service = InstantlyService(rate_limiter=rate_limiter)
        
        assert service.rate_limiter is rate_limiter
        assert service.api_key == 'test-api-key'
        
    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="INSTANTLY_API_KEY environment variable is not set"):
                InstantlyService()

    @patch('requests.post')
    def test_create_lead_success_without_rate_limiter(self, mock_post):
        """Test successful lead creation without rate limiter."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'lead-123',
            'campaign_id': 'camp-456',
            'email': 'test@example.com',
            'status': 'added'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test
        service = InstantlyService()
        result = service.create_lead('camp-456', 'test@example.com', 'John', 'Test personalization')
        
        # Verify
        assert result['id'] == 'lead-123'
        assert result['email'] == 'test@example.com'
        mock_post.assert_called_once_with(
            "https://api.instantly.ai/api/v2/leads",
            json={
                "campaign": 'camp-456',
                "email": 'test@example.com',
                "firstName": 'John',
                "personalization": 'Test personalization'
            },
            headers=service.headers,
            timeout=30
        )

    @patch('requests.post')
    def test_create_lead_success_with_rate_limiter(self, mock_post):
        """Test successful lead creation with rate limiter."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'lead-123',
            'email': 'test@example.com'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Setup mock rate limiter
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.execute.return_value = [1, True]
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Instantly', 100, 60)
        
        # Test
        service = InstantlyService(rate_limiter=rate_limiter)
        result = service.create_lead('camp-456', 'test@example.com', 'John', 'Test personalization')
        
        # Verify
        assert result['id'] == 'lead-123'
        assert result['email'] == 'test@example.com'
        mock_post.assert_called_once()

    def test_create_lead_rate_limit_exceeded(self):
        """Test lead creation when rate limit is exceeded."""
        # Setup mock rate limiter that denies requests
        mock_redis = Mock()
        mock_redis.get.return_value = '100'  # At limit
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.incr.return_value = 101  # Exceeds limit
        mock_redis.execute.return_value = [101, True]
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Instantly', 100, 60)
        
        # Test
        service = InstantlyService(rate_limiter=rate_limiter)
        result = service.create_lead('camp-456', 'test@example.com', 'John', 'Test personalization')
        
        # Verify rate limit response
        assert result['status'] == 'rate_limited'
        assert 'Rate limit exceeded' in result['error']
        assert 'remaining_requests' in result
        assert result['retry_after_seconds'] == 60

    @patch('requests.post')
    def test_create_lead_api_error(self, mock_post):
        """Test lead creation with API error."""
        # Setup mock to raise exception
        mock_post.side_effect = requests.RequestException("API Error")
        
        # Test
        service = InstantlyService()
        result = service.create_lead('camp-456', 'test@example.com', 'John', 'Test personalization')
        
        # Verify error response
        assert 'error' in result
        assert 'API Error' in result['error']
        assert 'payload' in result

    @patch('requests.post')
    def test_create_campaign_success_without_rate_limiter(self, mock_post):
        """Test successful campaign creation without rate limiter."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'campaign-123',
            'name': 'Test Campaign',
            'status': 'active'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test
        service = InstantlyService()
        result = service.create_campaign('Test Campaign')
        
        # Verify
        assert result['id'] == 'campaign-123'
        assert result['name'] == 'Test Campaign'
        mock_post.assert_called_once_with(
            "https://api.instantly.ai/api/v2/campaigns",
            json={
                "name": 'Test Campaign',
                "campaign_schedule": {
                    "schedules": [
                        {
                            "name": "My Schedule",
                            "timing": {
                                "from": "09:00",
                                "to": "17:00"
                            },
                            "days": {"monday": True},
                            "timezone": "Etc/GMT+12"
                        }
                    ]
                }
            },
            headers=service.headers,
            timeout=30
        )

    @patch('requests.post')
    def test_create_campaign_success_with_rate_limiter(self, mock_post):
        """Test successful campaign creation with rate limiter."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'campaign-123',
            'name': 'Test Campaign'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Setup mock rate limiter
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.execute.return_value = [1, True]
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Instantly', 100, 60)
        
        # Test
        service = InstantlyService(rate_limiter=rate_limiter)
        result = service.create_campaign('Test Campaign')
        
        # Verify
        assert result['id'] == 'campaign-123'
        assert result['name'] == 'Test Campaign'
        mock_post.assert_called_once()

    def test_create_campaign_rate_limit_exceeded(self):
        """Test campaign creation when rate limit is exceeded."""
        # Setup mock rate limiter that denies requests
        mock_redis = Mock()
        mock_redis.get.return_value = '100'  # At limit
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.incr.return_value = 101  # Exceeds limit
        mock_redis.execute.return_value = [101, True]
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Instantly', 100, 60)
        
        # Test
        service = InstantlyService(rate_limiter=rate_limiter)
        result = service.create_campaign('Test Campaign')
        
        # Verify rate limit response
        assert result['status'] == 'rate_limited'
        assert 'Rate limit exceeded' in result['error']
        assert 'remaining_requests' in result
        assert result['retry_after_seconds'] == 60

    @patch('requests.get')
    def test_get_campaign_analytics_success_without_rate_limiter(self, mock_get):
        """Test successful campaign analytics retrieval without rate limiter."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'campaign_id': 'camp-123',
            'sent': 100,
            'opens': 25,
            'clicks': 5
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test
        service = InstantlyService()
        result = service.get_campaign_analytics_overview('camp-123')
        
        # Verify
        assert result['campaign_id'] == 'camp-123'
        assert result['sent'] == 100
        mock_get.assert_called_once_with(
            "https://api.instantly.ai/api/v2/campaigns/analytics/overview",
            headers=service.headers,
            params={'id': 'camp-123'},
            timeout=30
        )

    @patch('requests.get')
    def test_get_campaign_analytics_success_with_rate_limiter(self, mock_get):
        """Test successful campaign analytics retrieval with rate limiter."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'campaign_id': 'camp-123',
            'sent': 100
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
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Instantly', 100, 60)
        
        # Test
        service = InstantlyService(rate_limiter=rate_limiter)
        result = service.get_campaign_analytics_overview('camp-123', '2024-01-01', '2024-01-31')
        
        # Verify
        assert result['campaign_id'] == 'camp-123'
        mock_get.assert_called_once()

    def test_get_campaign_analytics_rate_limit_exceeded(self):
        """Test campaign analytics retrieval when rate limit is exceeded."""
        # Setup mock rate limiter that denies requests
        mock_redis = Mock()
        mock_redis.get.return_value = '100'  # At limit
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.incr.return_value = 101  # Exceeds limit
        mock_redis.execute.return_value = [101, True]
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Instantly', 100, 60)
        
        # Test
        service = InstantlyService(rate_limiter=rate_limiter)
        result = service.get_campaign_analytics_overview('camp-123')
        
        # Verify rate limit response
        assert result['status'] == 'rate_limited'
        assert 'Rate limit exceeded' in result['error']
        assert 'remaining_requests' in result
        assert result['retry_after_seconds'] == 60

    def test_rate_limiter_failure_graceful_degradation(self):
        """Test that rate limiter failures don't prevent API calls."""
        # Setup mock rate limiter that fails
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis connection failed")
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Instantly', 100, 60)
        
        with patch('requests.post') as mock_post:
            # Setup successful API response
            mock_response = Mock()
            mock_response.json.return_value = {'id': 'lead-123', 'email': 'test@example.com'}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # Test
            service = InstantlyService(rate_limiter=rate_limiter)
            result = service.create_lead('camp-456', 'test@example.com', 'John', 'Test')
            
            # Verify that API call still succeeded despite rate limiter failure
            assert result['id'] == 'lead-123'
            assert result['email'] == 'test@example.com'
            mock_post.assert_called_once()

    def test_all_methods_with_mock_redis_integration(self):
        """Integration test with mock Redis for rate limiting behavior across all methods."""
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
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Instantly', 1, 60)
        service = InstantlyService(rate_limiter=rate_limiter)
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {'id': 'lead-123'}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # First call should succeed
            result1 = service.create_lead('camp-456', 'test1@example.com', 'John', 'Test')
            assert result1['id'] == 'lead-123'
            
            # Second call should be rate limited
            result2 = service.create_lead('camp-456', 'test2@example.com', 'Jane', 'Test')
            assert result2['status'] == 'rate_limited'

# Integration tests that could be run with actual Redis (when available)
class TestInstantlyServiceIntegration:
    """Integration tests for InstantlyService (require Redis)."""
    
    @pytest.mark.skip(reason="Requires Redis connection and API key")
    def test_real_rate_limiter_integration(self):
        """Test with real Redis connection (skipped by default)."""
        # This test would require actual Redis and API setup
        # Uncomment and configure when running integration tests
        pass

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"]) 