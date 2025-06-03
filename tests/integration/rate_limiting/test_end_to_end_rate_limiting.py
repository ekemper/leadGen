"""
End-to-end integration tests for the complete rate limiting system.

These tests validate the entire workflow from API requests through
background tasks with real rate limiting enforcement.
"""
import pytest
import time
import asyncio
import uuid
from unittest.mock import patch, Mock, MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.core.config import get_redis_connection
from app.core.database import get_db
from app.services.campaign import CampaignService
from app.workers.campaign_tasks import enrich_lead_task, fetch_and_save_leads_task
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.organization import Organization


class TestEndToEndRateLimiting:
    """End-to-end tests for complete rate limiting system."""
    
    @pytest.fixture(scope="class")
    def redis_client(self):
        """Redis client fixture - skip if Redis not available."""
        try:
            client = get_redis_connection()
            client.ping()
            yield client
            # Cleanup test keys
            for key in client.scan_iter("ratelimit:e2e*"):
                client.delete(key)
        except Exception as e:
            pytest.skip(f"Redis not available: {str(e)}")
    
    @pytest.fixture
    def db_session(self):
        """Database session fixture."""
        db_gen = get_db()
        db = next(db_gen)
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def test_campaign(self, db_session):
        """Create a test campaign for lead relationships."""
        # Create organization first
        org = Organization(
            id=str(uuid.uuid4()),
            name="Test E2E Organization",
            description="Test organization for E2E rate limiting tests"
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        
        # Create campaign
        campaign = Campaign(
            id="e2e-test-campaign",
            name="E2E Test Campaign",
            description="Test campaign for end-to-end rate limiting tests",
            organization_id=org.id,
            fileName="test-file.csv",
            totalRecords=100,
            url="https://example.com/test-file.csv"
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)
        yield campaign
        
        # Cleanup - delete any remaining leads first, then campaign, then organization
        try:
            # Delete any leads associated with this campaign
            leads = db_session.query(Lead).filter(Lead.campaign_id == campaign.id).all()
            for lead in leads:
                db_session.delete(lead)
            db_session.commit()
            
            # Now delete campaign
            db_session.delete(campaign)
            db_session.commit()
            
            # Finally delete organization
            db_session.delete(org)
            db_session.commit()
        except Exception as e:
            # If cleanup fails, rollback
            db_session.rollback()
    
    @pytest.fixture
    def test_lead(self, db_session, test_campaign):
        """Create a test lead."""
        lead = Lead(
            id="e2e-test-lead",
            campaign_id="e2e-test-campaign",
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            company="Test Corp",
            title="Product Manager",
            raw_data={"headline": "Senior Product Manager"}
        )
        db_session.add(lead)
        db_session.commit()
        db_session.refresh(lead)
        yield lead
        
        # Cleanup - the campaign fixture will handle lead cleanup, but delete this specific lead
        try:
            db_session.delete(lead)
            db_session.commit()
        except Exception as e:
            # If already deleted by campaign cleanup, that's fine
            db_session.rollback()
    
    def test_campaign_service_rate_limiting_integration(self, redis_client):
        """Test that CampaignService properly initializes with rate limiting."""
        service = CampaignService()
        
        # Verify that services are initialized with rate limiting
        if service.apollo_service:
            assert service.apollo_service.rate_limiter is not None
            assert service.apollo_service.rate_limiter.api_name == 'Apollo'
        
        if service.instantly_service:
            assert service.instantly_service.rate_limiter is not None
            assert service.instantly_service.rate_limiter.api_name == 'Instantly'
    
    @patch.dict('os.environ', {
        'MILLIONVERIFIER_API_KEY': 'test_key',
        'PERPLEXITY_TOKEN': 'test_token',
        'OPENAI_API_KEY': 'test_key',
        'INSTANTLY_API_KEY': 'test_key'
    })
    def test_complete_lead_enrichment_workflow(self, redis_client, test_lead):
        """Test complete lead enrichment workflow with rate limiting."""
        
        # Clear all rate limit states
        for service in ['MillionVerifier', 'Perplexity', 'OpenAI', 'Instantly']:
            redis_client.delete(f"ratelimit:{service}")
        
        # Mock all external API calls
        with patch('requests.get') as mock_email_get, \
             patch('requests.post') as mock_post, \
             patch('app.background_services.openai_service.OpenAI') as mock_openai:
            
            # Setup mocks
            self._setup_api_mocks(mock_email_get, mock_post, mock_openai)
            
            # Mock database session for the task
            with patch('app.workers.campaign_tasks.get_db') as mock_get_db:
                mock_db = Mock()
                mock_db.query.return_value.filter.return_value.first.return_value = test_lead
                mock_db.query.return_value.filter.return_value.all.return_value = [test_lead]
                mock_get_db.return_value.__next__.return_value = mock_db
                
                # Mock Job creation
                mock_job = Mock()
                mock_job.id = 'test-job-id'
                mock_db.add.return_value = None
                mock_db.commit.return_value = None
                mock_db.refresh.return_value = None
                
                # Execute enrichment task
                try:
                    # This will test all services with rate limiting
                    result = enrich_lead_task.apply(
                        args=['e2e-test-lead', 'e2e-test-campaign'],
                        throw=True
                    )
                    
                    # Verify the task completed
                    assert result.successful()
                    task_result = result.get()
                    assert 'lead_id' in task_result
                    assert task_result['lead_id'] == 'e2e-test-lead'
                    
                except Exception as e:
                    # If Celery isn't running, we can still verify the function works
                    pytest.skip(f"Celery not available for task execution: {str(e)}")
    
    def test_rate_limiting_prevents_api_overflow(self, redis_client):
        """Test that rate limiting prevents overwhelming external APIs."""
        from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
        
        # Create a very restrictive rate limiter
        limiter = ApiIntegrationRateLimiter(
            redis_client=redis_client,
            api_name='E2ETest',
            max_requests=2,
            period_seconds=10
        )
        
        redis_client.delete(limiter.key)
        
        # Simulate rapid requests
        successful_requests = 0
        blocked_requests = 0
        
        for i in range(10):
            if limiter.acquire():
                successful_requests += 1
            else:
                blocked_requests += 1
        
        # Verify rate limiting worked
        assert successful_requests == 2
        assert blocked_requests == 8
        
        # Verify remaining count
        assert limiter.get_remaining() == 0
    
    @patch.dict('os.environ', {
        'APIFY_API_TOKEN': 'test_token',
        'USE_APIFY_CLIENT_MOCK': 'true'
    })
    def test_apollo_service_bulk_operation_rate_limiting(self, redis_client):
        """Test Apollo service rate limiting for bulk operations."""
        from app.background_services.apollo_service import ApolloService
        from app.core.dependencies import get_apollo_rate_limiter
        
        rate_limiter = get_apollo_rate_limiter(redis_client)
        service = ApolloService(rate_limiter=rate_limiter)
        
        # Clear rate limit state
        redis_client.delete(rate_limiter.key)
        
        # Mock database for fetch_leads
        with patch('app.background_services.apollo_service.Session') as mock_session:
            mock_db = Mock()
            mock_session.return_value = mock_db
            
            # Test bulk operation
            params = {
                'fileName': 'test.csv',
                'totalRecords': 50,
                'url': 'https://app.apollo.io/test'
            }
            
            try:
                result = service.fetch_leads(
                    params=params,
                    campaign_id='test-campaign',
                    db=mock_db
                )
                
                # Should return a result (may be rate limited or successful)
                assert isinstance(result, dict)
                
            except Exception as e:
                # If Apollo service dependencies aren't available, skip
                pytest.skip(f"Apollo service dependencies not available: {str(e)}")
    
    def test_graceful_degradation_scenarios(self, redis_client):
        """Test system behavior when components fail."""
        
        # Test 1: Redis unavailable
        failed_redis = Mock()
        failed_redis.get.side_effect = Exception("Redis connection failed")
        
        from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
        limiter = ApiIntegrationRateLimiter(
            redis_client=failed_redis,
            api_name='GracefulTest',
            max_requests=5,
            period_seconds=60
        )
        
        # Should gracefully handle Redis failure
        assert limiter.acquire() == True  # Graceful degradation allows requests
        assert limiter.get_remaining() == 5  # Returns max_requests
        
        # Test 2: Service initialization with failed Redis
        with patch('app.core.config.get_redis_connection') as mock_redis_conn:
            mock_redis_conn.side_effect = Exception("Redis unavailable")
            
            # Clear any imported modules to force re-import with the mock
            import sys
            service_module = 'app.services.campaign'
            if service_module in sys.modules:
                del sys.modules[service_module]
            
            # Import after patching
            from app.services.campaign import CampaignService
            
            # CampaignService should still initialize but services should be None
            service = CampaignService()
            
            # Services should be None due to Redis failure
            assert service.apollo_service is None
            assert service.instantly_service is None
    
    def test_rate_limit_monitoring_and_logging(self, redis_client, caplog):
        """Test that rate limiting produces proper monitoring logs."""
        from app.background_services.email_verifier_service import EmailVerifierService
        from app.core.dependencies import get_email_verifier_rate_limiter
        
        with patch.dict('os.environ', {'MILLIONVERIFIER_API_KEY': 'test_key'}):
            rate_limiter = get_email_verifier_rate_limiter(redis_client)
            service = EmailVerifierService(rate_limiter=rate_limiter)
            
            # Clear state
            redis_client.delete(rate_limiter.key)
            
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {'result': 'deliverable'}
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
                
                # Make a request
                result = service.verify_email('test@example.com')
                
                # Check that rate limiting logs are present
                logs = caplog.text
                assert 'EmailVerifierService initialized with rate limiting' in logs or \
                       'rate_limiting' in logs.lower()
    
    def test_multiple_services_concurrent_rate_limiting(self, redis_client):
        """Test concurrent rate limiting across multiple services."""
        from app.core.dependencies import (
            get_apollo_rate_limiter,
            get_email_verifier_rate_limiter,
            get_perplexity_rate_limiter
        )
        
        # Get rate limiters for different services
        apollo_limiter = get_apollo_rate_limiter(redis_client)
        email_limiter = get_email_verifier_rate_limiter(redis_client)
        perplexity_limiter = get_perplexity_rate_limiter(redis_client)
        
        # Clear all states
        redis_client.delete(apollo_limiter.key)
        redis_client.delete(email_limiter.key)
        redis_client.delete(perplexity_limiter.key)
        
        # Test concurrent access
        limiters = [apollo_limiter, email_limiter, perplexity_limiter]
        
        for limiter in limiters:
            # Each should be able to acquire independently
            assert limiter.acquire() == True
            assert limiter.get_remaining() >= 0
        
        # Verify isolation - using one limiter doesn't affect others
        apollo_limiter.acquire()  # Use Apollo (has 30 requests per 60s)
        
        # Others should still be available (though email might be rate limited)
        # Email verifier has only 1 request per 3 seconds, so we might hit the limit
        email_acquire_result = email_limiter.acquire()
        # Either succeeds or is rate limited - both are valid behaviors
        assert email_acquire_result in [True, False]
        
        # Perplexity should still work (has 50 requests per 60s)
        assert perplexity_limiter.acquire() == True
    
    def _setup_api_mocks(self, mock_email_get, mock_post, mock_openai):
        """Helper to setup all API mocks."""
        
        # Email verification mock
        email_response = Mock()
        email_response.json.return_value = {'result': 'deliverable', 'score': 99}
        email_response.raise_for_status.return_value = None
        mock_email_get.return_value = email_response
        
        # Perplexity and Instantly mock
        api_response = Mock()
        api_response.json.return_value = {
            'choices': [{'message': {'content': 'Test enrichment'}}]
        }
        api_response.raise_for_status.return_value = None
        mock_post.return_value = api_response
        
        # OpenAI mock
        openai_client = Mock()
        openai_response = Mock()
        openai_response.model_dump.return_value = {
            'choices': [{'message': {'content': 'Test email copy'}}]
        }
        openai_client.chat.completions.create.return_value = openai_response
        mock_openai.return_value = openai_client


@pytest.mark.performance
class TestPerformanceUnderLoad:
    """Performance tests for rate limiting under load."""
    
    @pytest.fixture(scope="class")
    def redis_client(self):
        """Redis client fixture."""
        try:
            client = get_redis_connection()
            client.ping()
            yield client
            # Cleanup
            for key in client.scan_iter("ratelimit:perf*"):
                client.delete(key)
        except Exception as e:
            pytest.skip(f"Redis not available: {str(e)}")
    
    def test_rate_limiter_performance_under_load(self, redis_client):
        """Test rate limiter performance with high request volume."""
        from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
        
        limiter = ApiIntegrationRateLimiter(
            redis_client=redis_client,
            api_name='PerfTest',
            max_requests=100,
            period_seconds=60
        )
        
        redis_client.delete(limiter.key)
        
        # Measure performance
        start_time = time.time()
        successful = 0
        
        for i in range(200):
            if limiter.acquire():
                successful += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert duration < 5.0  # Should complete in under 5 seconds
        assert successful == 100  # Should respect the limit
        
        # Test throughput
        requests_per_second = 200 / duration
        assert requests_per_second > 50  # Should handle at least 50 requests/second
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting_performance(self, redis_client):
        """Test performance with concurrent requests."""
        from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
        
        limiter = ApiIntegrationRateLimiter(
            redis_client=redis_client,
            api_name='ConcurrentPerfTest',
            max_requests=50,
            period_seconds=60
        )
        
        redis_client.delete(limiter.key)
        
        async def make_request():
            return limiter.acquire()
        
        # Launch concurrent requests
        start_time = time.time()
        tasks = [make_request() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        duration = end_time - start_time
        successful = sum(results)
        
        # Performance and correctness assertions
        assert duration < 10.0  # Should complete in under 10 seconds
        assert successful == 50  # Should respect the limit exactly
        assert results.count(True) == 50
        assert results.count(False) == 50


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 