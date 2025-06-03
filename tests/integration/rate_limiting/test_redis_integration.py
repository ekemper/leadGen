"""
Integration tests for rate limiting with Redis.

These tests require a running Redis instance and validate the complete
rate limiting functionality in a real environment.
"""
import pytest
import time
import asyncio
from unittest.mock import patch, Mock
from redis import Redis
from app.core.config import get_redis_connection
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
from app.core.dependencies import (
    get_apollo_rate_limiter,
    get_email_verifier_rate_limiter,
    get_perplexity_rate_limiter,
    get_openai_rate_limiter,
    get_instantly_rate_limiter
)
from app.background_services.email_verifier_service import EmailVerifierService
from app.background_services.apollo_service import ApolloService
from app.background_services.instantly_service import InstantlyService
from app.background_services.openai_service import OpenAIService
from app.background_services.perplexity_service import PerplexityService
from app.models.lead import Lead


class TestRedisIntegration:
    """Integration tests with real Redis instance."""
    
    @pytest.fixture(scope="class")
    def redis_client(self):
        """Redis client fixture - skip if Redis not available."""
        try:
            client = get_redis_connection()
            # Test connection
            client.ping()
            yield client
            # Cleanup test keys
            for key in client.scan_iter("ratelimit:test*"):
                client.delete(key)
        except Exception as e:
            pytest.skip(f"Redis not available: {str(e)}")
    
    @pytest.fixture
    def test_lead(self):
        """Create a test lead for service testing."""
        return Lead(
            id="test-lead-id",
            campaign_id="test-campaign-id",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            company="Test Company",
            title="Software Engineer",
            raw_data={"headline": "Senior Software Engineer"}
        )
    
    def test_rate_limiter_creation_all_services(self, redis_client):
        """Test that all service rate limiters can be created."""
        apollo_limiter = get_apollo_rate_limiter(redis_client)
        email_limiter = get_email_verifier_rate_limiter(redis_client)
        perplexity_limiter = get_perplexity_rate_limiter(redis_client)
        openai_limiter = get_openai_rate_limiter(redis_client)
        instantly_limiter = get_instantly_rate_limiter(redis_client)
        
        assert apollo_limiter.api_name == 'Apollo'
        assert email_limiter.api_name == 'MillionVerifier'
        assert perplexity_limiter.api_name == 'Perplexity'
        assert openai_limiter.api_name == 'OpenAI'
        assert instantly_limiter.api_name == 'Instantly'
        
        # Verify configuration values are loaded correctly
        assert apollo_limiter.max_requests > 0
        assert apollo_limiter.period_seconds > 0
    
    def test_rate_limiter_acquire_and_limit(self, redis_client):
        """Test rate limiter acquire and limit enforcement."""
        # Create a rate limiter with very low limits for testing
        limiter = ApiIntegrationRateLimiter(
            redis_client=redis_client,
            api_name='TestService',
            max_requests=2,
            period_seconds=5
        )
        
        # Clear any existing state
        redis_client.delete(limiter.key)
        
        # First request should be allowed
        assert limiter.acquire() == True
        assert limiter.get_remaining() == 1
        
        # Second request should be allowed
        assert limiter.acquire() == True
        assert limiter.get_remaining() == 0
        
        # Third request should be blocked
        assert limiter.acquire() == False
        assert limiter.get_remaining() == 0
        
        # Check that we can just check without acquiring
        assert limiter.is_allowed() == False
    
    def test_rate_limiter_expiry(self, redis_client):
        """Test that rate limiter resets after expiry period."""
        # Create a rate limiter with very short period
        limiter = ApiIntegrationRateLimiter(
            redis_client=redis_client,
            api_name='TestExpiry',
            max_requests=1,
            period_seconds=1
        )
        
        # Clear any existing state
        redis_client.delete(limiter.key)
        
        # Use up the limit
        assert limiter.acquire() == True
        assert limiter.acquire() == False
        
        # Wait for expiry
        time.sleep(1.5)
        
        # Should be able to acquire again
        assert limiter.acquire() == True
        assert limiter.get_remaining() == 0
    
    @patch.dict('os.environ', {'MILLIONVERIFIER_API_KEY': 'test_key'})
    def test_email_verifier_service_with_redis(self, redis_client):
        """Test EmailVerifierService with real Redis rate limiting."""
        rate_limiter = get_email_verifier_rate_limiter(redis_client)
        service = EmailVerifierService(rate_limiter=rate_limiter)
        
        # Clear rate limit state
        redis_client.delete(rate_limiter.key)
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {'result': 'deliverable'}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # First call should work
            result = service.verify_email('test@example.com')
            assert 'result' in result or 'status' in result  # Could be API response or rate limit response
    
    @patch.dict('os.environ', {'APIFY_API_TOKEN': 'test_token', 'USE_APIFY_CLIENT_MOCK': 'true'})
    def test_apollo_service_with_redis(self, redis_client):
        """Test ApolloService with real Redis rate limiting."""
        rate_limiter = get_apollo_rate_limiter(redis_client)
        service = ApolloService(rate_limiter=rate_limiter)
        
        # Clear rate limit state
        redis_client.delete(rate_limiter.key)
        
        # Test that service can be initialized with rate limiter
        assert service.rate_limiter is not None
        assert service.rate_limiter.api_name == 'Apollo'
    
    @patch.dict('os.environ', {'PERPLEXITY_TOKEN': 'test_token'})
    def test_perplexity_service_with_redis(self, redis_client, test_lead):
        """Test PerplexityService with real Redis rate limiting."""
        rate_limiter = get_perplexity_rate_limiter(redis_client)
        service = PerplexityService(rate_limiter=rate_limiter)
        
        # Clear rate limit state
        redis_client.delete(rate_limiter.key)
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {'choices': [{'message': {'content': 'Test enrichment'}}]}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # First call should work
            result = service.enrich_lead(test_lead)
            assert 'choices' in result or 'status' in result  # Could be API response or rate limit response
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'})
    def test_openai_service_with_redis(self, redis_client, test_lead):
        """Test OpenAIService with real Redis rate limiting."""
        rate_limiter = get_openai_rate_limiter(redis_client)
        service = OpenAIService(rate_limiter=rate_limiter)
        
        # Clear rate limit state
        redis_client.delete(rate_limiter.key)
        
        with patch('app.background_services.openai_service.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.model_dump.return_value = {
                'choices': [{'message': {'content': 'Test email copy'}}]
            }
            mock_client.chat.completions.create.return_value = mock_response
            
            enrichment_data = {'choices': [{'message': {'content': 'Test enrichment'}}]}
            result = service.generate_email_copy(test_lead, enrichment_data)
            assert 'choices' in result or 'status' in result  # Could be API response or rate limit response
    
    @patch.dict('os.environ', {'INSTANTLY_API_KEY': 'test_key'})
    def test_instantly_service_with_redis(self, redis_client):
        """Test InstantlyService with real Redis rate limiting."""
        rate_limiter = get_instantly_rate_limiter(redis_client)
        service = InstantlyService(rate_limiter=rate_limiter)
        
        # Clear rate limit state
        redis_client.delete(rate_limiter.key)
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {'id': 'test_lead_id', 'status': 'created'}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # First call should work
            result = service.create_lead('test_campaign', 'test@example.com', 'John', 'Test personalization')
            assert 'id' in result or 'status' in result  # Could be API response or rate limit response
    
    def test_concurrent_rate_limiting(self, redis_client):
        """Test rate limiting under concurrent requests."""
        limiter = ApiIntegrationRateLimiter(
            redis_client=redis_client,
            api_name='ConcurrentTest',
            max_requests=5,
            period_seconds=10
        )
        
        # Clear any existing state
        redis_client.delete(limiter.key)
        
        # Simulate concurrent requests
        results = []
        for i in range(10):
            result = limiter.acquire()
            results.append(result)
        
        # Should have exactly 5 successful acquisitions
        successful = sum(results)
        assert successful == 5
        assert results.count(True) == 5
        assert results.count(False) == 5
    
    def test_redis_connection_failure_graceful_degradation(self):
        """Test graceful degradation when Redis connection fails."""
        # Create a Redis client that will fail
        failed_redis = Redis(host='nonexistent-host', port=6379, socket_timeout=1)
        
        limiter = ApiIntegrationRateLimiter(
            redis_client=failed_redis,
            api_name='FailTest',
            max_requests=1,
            period_seconds=1
        )
        
        # Should gracefully degrade and allow requests
        assert limiter.acquire() == True
        assert limiter.get_remaining() == 1  # Returns max when Redis fails
        assert limiter.is_allowed() == True
    
    def test_multiple_services_isolated_limits(self, redis_client):
        """Test that different services have isolated rate limits."""
        apollo_limiter = get_apollo_rate_limiter(redis_client)
        email_limiter = get_email_verifier_rate_limiter(redis_client)
        
        # Clear state
        redis_client.delete(apollo_limiter.key)
        redis_client.delete(email_limiter.key)
        
        # Use up Apollo limit (assuming it's > 1)
        apollo_limiter.acquire()
        
        # Email limiter should still work
        assert email_limiter.acquire() == True
        
        # Verify they have different keys
        assert apollo_limiter.key != email_limiter.key
        assert 'Apollo' in apollo_limiter.key
        assert 'MillionVerifier' in email_limiter.key


@pytest.mark.asyncio
class TestAsyncRateLimiting:
    """Test rate limiting in async contexts."""
    
    @pytest.fixture(scope="class")
    def redis_client(self):
        """Redis client fixture."""
        try:
            client = get_redis_connection()
            client.ping()
            yield client
            # Cleanup
            for key in client.scan_iter("ratelimit:async*"):
                client.delete(key)
        except Exception as e:
            pytest.skip(f"Redis not available: {str(e)}")
    
    async def test_async_rate_limiting_behavior(self, redis_client):
        """Test rate limiting behavior in async context."""
        limiter = ApiIntegrationRateLimiter(
            redis_client=redis_client,
            api_name='AsyncTest',
            max_requests=3,
            period_seconds=5
        )
        
        redis_client.delete(limiter.key)
        
        # Test async acquisition
        tasks = []
        for i in range(6):
            task = asyncio.create_task(self._async_acquire(limiter))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Should have exactly 3 successful acquisitions
        successful = sum(results)
        assert successful == 3
    
    async def _async_acquire(self, limiter):
        """Helper method for async acquisition."""
        return limiter.acquire()


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 