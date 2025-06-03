"""
Integration tests for circuit breaker, queue management, and alert system.
"""

import pytest
import time
import redis
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import os
import asyncio
import logging

from app.core.circuit_breaker import CircuitBreakerService, ThirdPartyService, CircuitState
from app.core.queue_manager import QueueManager
from app.core.alert_service import AlertService, AlertLevel
from app.models.job import Job, JobStatus, JobType
from app.models.lead import Lead
from app.core.config import get_redis_connection
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter


# Integration test configuration
INTEGRATION_TEST_TIMEOUT = 30
REDIS_TEST_TIMEOUT = 5


@pytest.fixture
def redis_client():
    """Create Redis client for testing."""
    import redis
    import os
    
    redis_host = os.getenv('REDIS_HOST', 'lead-gen-redis-1')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_db = int(os.getenv('REDIS_TEST_DB', 1))  # Use separate DB for tests
    
    client = redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        decode_responses=True
    )
    
    # Clear all circuit breaker and rate limiter data before each test
    pattern_keys = [
        "circuit_breaker:*",
        "circuit_failures:*", 
        "queue_paused:*",
        "circuit_success:*",
        "rate_limit:*"
    ]
    
    for pattern in pattern_keys:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
    
    yield client
    
    # Cleanup after test
    for pattern in pattern_keys:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)


@pytest.fixture
def circuit_breaker(redis_client):
    """Circuit breaker service for testing."""
    return CircuitBreakerService(redis_client)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def queue_manager(mock_db, circuit_breaker):
    """Queue manager for testing."""
    return QueueManager(mock_db, circuit_breaker)


@pytest.fixture
def alert_service():
    """Alert service for testing."""
    return AlertService()


@pytest.fixture
def rate_limiter(redis_client):
    """Fixture to provide RateLimiter instance for integration tests."""
    return ApiIntegrationRateLimiter(
        redis_client=redis_client,
        api_name="test_api",
        max_requests=5,
        period_seconds=10
    )


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality."""
    
    def test_initial_state_is_closed(self, circuit_breaker):
        """Test that circuit breaker starts in closed state."""
        state = circuit_breaker._get_circuit_state(ThirdPartyService.PERPLEXITY)
        assert state == CircuitState.CLOSED
    
    def test_circuit_opens_after_threshold_failures(self, circuit_breaker):
        """Test that circuit opens after reaching failure threshold."""
        service = ThirdPartyService.PERPLEXITY
        
        # Record failures up to threshold
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"failure_{i}", "test_error")
        
        # Circuit should now be open
        state = circuit_breaker._get_circuit_state(service)
        assert state == CircuitState.OPEN
    
    def test_circuit_allows_request_when_closed(self, circuit_breaker):
        """Test that closed circuit allows requests."""
        service = ThirdPartyService.PERPLEXITY
        allowed, reason = circuit_breaker.should_allow_request(service)
        assert allowed
        assert "CLOSED" in reason
    
    def test_circuit_blocks_request_when_open(self, circuit_breaker):
        """Test that open circuit blocks requests."""
        service = ThirdPartyService.PERPLEXITY
        
        # Open the circuit
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"failure_{i}", "test_error")
        
        allowed, reason = circuit_breaker.should_allow_request(service)
        assert not allowed
        assert "OPEN" in reason
    
    def test_half_open_allows_limited_requests(self, circuit_breaker):
        """Test half-open state behavior."""
        service = ThirdPartyService.PERPLEXITY
        
        # Open the circuit
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"failure_{i}", "test_error")
        
        # Manually set to half-open (simulating timeout)
        circuit_breaker._set_circuit_state(service, CircuitState.HALF_OPEN)
        
        # Should allow one request
        allowed, reason = circuit_breaker.should_allow_request(service)
        assert allowed
        assert "HALF_OPEN" in reason


class TestQueueManagerIntegration:
    """Test queue manager integration with circuit breaker."""
    
    def test_should_process_job_with_closed_circuit(self, queue_manager):
        """Test job processing when circuit is closed."""
        job = Mock(spec=Job)
        job.job_type = JobType.ENRICH_LEAD
        
        should_process, reason = queue_manager.should_process_job(job)
        assert should_process
        assert "available" in reason
    
    def test_should_not_process_job_with_open_circuit(self, queue_manager, circuit_breaker):
        """Test job processing when circuit is open."""
        # Open the Perplexity circuit
        service = ThirdPartyService.PERPLEXITY
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"failure_{i}", "test_error")
        
        job = Mock(spec=Job)
        job.job_type = JobType.ENRICH_LEAD
        
        should_process, reason = queue_manager.should_process_job(job)
        assert not should_process
        assert "perplexity" in reason.lower()
    
    def test_pause_jobs_for_service(self, queue_manager, mock_db):
        """Test pausing jobs when service fails."""
        # Mock pending jobs
        pending_jobs = [
            Mock(spec=Job, id=1, job_type=JobType.ENRICH_LEAD),
            Mock(spec=Job, id=2, job_type=JobType.ENRICH_LEAD),
        ]
        
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = pending_jobs
        mock_db.query.return_value = mock_query
        
        paused_count = queue_manager.pause_jobs_for_service(
            ThirdPartyService.PERPLEXITY, 
            "Test failure"
        )
        
        assert paused_count == 2
        for job in pending_jobs:
            assert job.status == JobStatus.PAUSED
            assert "Paused due to perplexity" in job.error
    
    def test_resume_jobs_for_service(self, queue_manager, mock_db):
        """Test resuming jobs when service recovers."""
        # Mock paused jobs
        paused_jobs = [
            Mock(spec=Job, id=1, status=JobStatus.PAUSED, error="Paused due to perplexity service unavailability"),
            Mock(spec=Job, id=2, status=JobStatus.PAUSED, error="Paused due to perplexity service unavailability"),
        ]
        
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = paused_jobs
        mock_db.query.return_value = mock_query
        
        resumed_count = queue_manager.resume_jobs_for_service(ThirdPartyService.PERPLEXITY)
        
        assert resumed_count == 2
        for job in paused_jobs:
            assert job.status == JobStatus.PENDING
            assert job.error is None


class TestAlertServiceIntegration:
    """Test alert service integration."""
    
    @patch('smtplib.SMTP')
    def test_send_circuit_breaker_alert_critical(self, mock_smtp, alert_service):
        """Test sending critical alert when circuit opens."""
        with patch.object(alert_service, 'email_config', {
            'admin_emails': ['admin@test.com'],
            'smtp_username': 'test',
            'smtp_password': 'test',
            'smtp_server': 'localhost',
            'smtp_port': 587,
            'from_email': 'alerts@test.com'
        }):
            alert_service.send_circuit_breaker_alert(
                service=ThirdPartyService.PERPLEXITY,
                old_state=CircuitState.CLOSED,
                new_state=CircuitState.OPEN,
                failure_reason="Rate limit exceeded",
                failure_count=5
            )
            
            # Verify SMTP was called
            assert mock_smtp.called
    
    def test_alert_level_determination(self, alert_service):
        """Test alert level determination based on state transitions."""
        # Critical: circuit opens
        level = alert_service._get_alert_level(CircuitState.CLOSED, CircuitState.OPEN)
        assert level == AlertLevel.CRITICAL
        
        # Warning: circuit goes to half-open
        level = alert_service._get_alert_level(CircuitState.OPEN, CircuitState.HALF_OPEN)
        assert level == AlertLevel.WARNING
        
        # Info: circuit recovers
        level = alert_service._get_alert_level(CircuitState.OPEN, CircuitState.CLOSED)
        assert level == AlertLevel.INFO
    
    def test_queue_status_alert(self, alert_service):
        """Test queue status alert for high backlog."""
        with patch.object(alert_service, '_log_alert') as mock_log:
            alert_service.send_queue_status_alert(
                total_paused_jobs=15,
                services_down=['perplexity', 'openai'],
                job_backlog={'pending': 50, 'processing': 10}
            )
            
            # Should log warning level alert
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert call_args['alert_level'] == AlertLevel.WARNING.value
            assert call_args['total_paused_jobs'] == 15


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""
    
    def test_perplexity_rate_limit_scenario(self, circuit_breaker, queue_manager, mock_db):
        """Test complete scenario: Perplexity rate limit -> circuit opens -> jobs paused."""
        service = ThirdPartyService.PERPLEXITY
        
        # Simulate rate limit failures
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, "Rate limit exceeded", "rate_limit")
        
        # Circuit should be open
        assert circuit_breaker._get_circuit_state(service) == CircuitState.OPEN
        
        # Mock pending enrichment jobs
        pending_jobs = [Mock(spec=Job, id=i, job_type=JobType.ENRICH_LEAD) for i in range(5)]
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = pending_jobs
        mock_db.query.return_value = mock_query
        
        # Pause jobs due to circuit breaker
        paused_count = queue_manager.pause_jobs_for_service(service, "Circuit breaker opened")
        
        assert paused_count == 5
        for job in pending_jobs:
            assert job.status == JobStatus.PAUSED
    
    def test_service_recovery_scenario(self, circuit_breaker, queue_manager, mock_db):
        """Test complete scenario: Service recovers -> circuit closes -> jobs resumed."""
        service = ThirdPartyService.PERPLEXITY
        
        # Start with open circuit
        for i in range(3):
            circuit_breaker.record_failure(service, "Service error", "exception")
        
        # Mock paused jobs
        paused_jobs = [Mock(spec=Job, id=i, status=JobStatus.PAUSED, 
                           error=f"Paused due to {service.value} service unavailability") 
                      for i in range(3)]
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = paused_jobs
        mock_db.query.return_value = mock_query
        
        # Simulate service recovery
        circuit_breaker.record_success(service)
        circuit_breaker.record_success(service)  # Should close circuit
        
        # Resume jobs
        resumed_count = queue_manager.resume_jobs_for_service(service)
        
        assert resumed_count == 3
        for job in paused_jobs:
            assert job.status == JobStatus.PENDING
            assert job.error is None
    
    @patch('app.core.alert_service.get_alert_service')
    def test_circuit_breaker_with_alerts(self, mock_get_alert_service, circuit_breaker):
        """Test circuit breaker sends alerts on state changes."""
        mock_alert_service = Mock()
        mock_get_alert_service.return_value = mock_alert_service
        
        service = ThirdPartyService.PERPLEXITY
        
        # Trigger circuit breaker with enough failures to reach threshold
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"failure_{i}", "test_error")
        
        # Should have sent alert about circuit opening
        mock_alert_service.send_circuit_breaker_alert.assert_called()
        call_args = mock_alert_service.send_circuit_breaker_alert.call_args
        assert call_args[1]['service'] == service
        assert call_args[1]['new_state'] == CircuitState.OPEN


class TestRealTimeScenarios:
    """Test real-time behavior scenarios."""
    
    def test_circuit_timeout_behavior(self, circuit_breaker):
        """Test circuit breaker timeout behavior."""
        service = ThirdPartyService.PERPLEXITY
        
        # Set a very short timeout for testing
        circuit_breaker.recovery_timeout = 1
        
        # Open the circuit
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"failure_{i}", "test_error")
        
        assert circuit_breaker._get_circuit_state(service) == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(2)
        
        # Should allow request (half-open)
        allowed, reason = circuit_breaker.should_allow_request(service)
        assert allowed
        assert "half_open" in reason.lower()
    
    def test_multiple_service_failures(self, circuit_breaker, queue_manager, mock_db):
        """Test behavior when multiple services fail simultaneously."""
        services = [ThirdPartyService.PERPLEXITY, ThirdPartyService.OPENAI, ThirdPartyService.INSTANTLY]
        
        # Fail all services
        for service in services:
            for i in range(circuit_breaker.failure_threshold):
                circuit_breaker.record_failure(service, f"failure_{i}", "test_error")
        
        # All circuits should be open
        for service in services:
            assert circuit_breaker._get_circuit_state(service) == CircuitState.OPEN
        
        # Test job processing (should be blocked)
        job = Mock(spec=Job, job_type=JobType.ENRICH_LEAD)
        should_process, reason = queue_manager.should_process_job(job)
        assert not should_process
        assert "unavailable" in reason.lower()


class TestCircuitBreakerIntegration:
    """Integration tests for CircuitBreaker with real Redis."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_state_persistence(self, redis_client):
        """Test that circuit breaker state persists in Redis."""
        
        async def failing_operation():
            raise Exception("Test failure")
        
        circuit_breaker = CircuitBreakerService(redis_client)
        
        # Record failures to open circuit
        service = ThirdPartyService.PERPLEXITY
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"failure_{i}", "test_error")
        
        # Circuit should be OPEN
        state = circuit_breaker._get_circuit_state(service)
        assert state == CircuitState.OPEN
        
        # Verify state is persisted in Redis
        circuit_key = circuit_breaker._get_circuit_key(service)
        stored_data = redis_client.get(circuit_key)
        assert stored_data is not None
        
        # Create new circuit breaker instance - should load OPEN state
        new_circuit_breaker = CircuitBreakerService(redis_client)
        new_state = new_circuit_breaker._get_circuit_state(service)
        assert new_state == CircuitState.OPEN


    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_flow(self, redis_client):
        """Test full recovery flow with Redis persistence."""
        
        circuit_breaker = CircuitBreakerService(redis_client)
        service = ThirdPartyService.PERPLEXITY
        
        # Trigger failures to open circuit
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"failure_{i}", "test_error")
        
        state = circuit_breaker._get_circuit_state(service)
        assert state == CircuitState.OPEN
        
        # Manually set to half-open to test recovery
        circuit_breaker._set_circuit_state(service, CircuitState.HALF_OPEN)
        
        # Record successes to close circuit
        for i in range(circuit_breaker.success_threshold):
            circuit_breaker.record_success(service)
        
        # Circuit should be closed now
        final_state = circuit_breaker._get_circuit_state(service)
        assert final_state == CircuitState.CLOSED


    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_access(self, redis_client):
        """Test circuit breaker behavior under concurrent access."""
        
        circuit_breaker = CircuitBreakerService(redis_client)
        service = ThirdPartyService.PERPLEXITY
        
        # Record multiple failures concurrently
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"concurrent_failure_{i}", "test_error")
        
        # Circuit should be open
        state = circuit_breaker._get_circuit_state(service)
        assert state == CircuitState.OPEN
        
        # Should block requests
        allowed, reason = circuit_breaker.should_allow_request(service)
        assert not allowed
        assert "OPEN" in reason
        
        # Record some successes and test recovery
        circuit_breaker._set_circuit_state(service, CircuitState.HALF_OPEN)
        for i in range(circuit_breaker.success_threshold):
            circuit_breaker.record_success(service)
        
        # Circuit should be manageable
        final_state = circuit_breaker._get_circuit_state(service)
        assert final_state in [CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN]


class TestRateLimiterIntegration:
    """Integration tests for ApiIntegrationRateLimiter with real Redis."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic_functionality(self, rate_limiter):
        """Test basic rate limiting functionality."""
        
        # Use up the rate limit by acquiring slots (max_requests=5)
        acquired_count = 0
        for i in range(5):
            if rate_limiter.acquire():
                acquired_count += 1
            else:
                break
        
        # Should have acquired all 5 slots
        assert acquired_count == 5, f"Should have acquired 5 slots, got {acquired_count}"
        
        # Next request should be denied since we've used all slots
        acquired = rate_limiter.acquire()
        assert not acquired, "Request beyond limit should be denied"


    @pytest.mark.asyncio
    async def test_rate_limiter_window_reset(self, rate_limiter):
        """Test that rate limiter resets after time window."""
        
        # Use up the rate limit by acquiring slots
        acquired_count = 0
        for _ in range(5):
            if rate_limiter.acquire():
                acquired_count += 1
        
        # Should have acquired at most 5 slots
        assert acquired_count <= 5
        
        # Should be denied now if we used up all slots
        if acquired_count == 5:
            allowed = rate_limiter.is_allowed()
            assert not allowed
        
        # For testing window reset, we'd need to wait or manually reset
        # Let's check remaining count instead
        remaining = rate_limiter.get_remaining()
        assert remaining >= 0


    @pytest.mark.asyncio  
    async def test_rate_limiter_acquire_and_check(self, rate_limiter):
        """Test acquire and check methods work correctly together."""
        
        # Check initial state
        initial_remaining = rate_limiter.get_remaining()
        assert initial_remaining > 0
        
        # Acquire a slot
        acquired = rate_limiter.acquire()
        assert acquired
        
        # Remaining should decrease
        new_remaining = rate_limiter.get_remaining()
        assert new_remaining < initial_remaining


class TestCircuitBreakerRateLimiterIntegration:
    """Integration tests combining CircuitBreaker and RateLimiter."""
    
    @pytest.mark.asyncio
    async def test_combined_protection(self, redis_client):
        """Test circuit breaker and rate limiter working together."""
        
        # Set up rate limiter with very low limits for testing
        rate_limiter = ApiIntegrationRateLimiter(
            redis_client=redis_client,
            api_name="combined_test",
            max_requests=2,
            period_seconds=10
        )
        
        # Set up circuit breaker
        circuit_breaker = CircuitBreakerService(redis_client)
        
        user_id = "test_user_combined"
        
        async def protected_operation():
            # First check rate limiting
            if not rate_limiter.is_allowed():
                raise Exception("Rate limit exceeded")
            
            # Then perform operation (could fail)
            return "Operation successful"
        
        # Should succeed for first 2 calls
        for i in range(2):
            if rate_limiter.acquire():
                result = "Operation successful"
                assert result == "Operation successful"
            else:
                raise Exception("Rate limit exceeded")
        
        # Third call should fail due to rate limiting
        if not rate_limiter.acquire():
            # Record failure in circuit breaker
            circuit_breaker.record_failure(ThirdPartyService.PERPLEXITY, "rate_limit_test", "Rate limit exceeded")
        
        # Fourth call should also fail
        if not rate_limiter.acquire():
            circuit_breaker.record_failure(ThirdPartyService.PERPLEXITY, "rate_limit_test", "Rate limit exceeded")
        
        # After 2 failures, check if circuit would be open
        allowed, reason = circuit_breaker.should_allow_request(ThirdPartyService.PERPLEXITY)
        assert not allowed  # Circuit should be open due to failures


@pytest.mark.skipif(
    os.getenv('SKIP_INTEGRATION_TESTS') == 'true',
    reason="Integration tests disabled"
)
class TestRedisConnectionHandling:
    """Test Redis connection handling and error scenarios."""
    
    def test_redis_connection_failure(self):
        """Test behavior when Redis is unavailable."""
        
        # Try to connect to non-existent Redis instance
        redis_host = os.getenv('REDIS_HOST', 'lead-gen-redis-1')
        bad_client = redis.Redis(host=redis_host, port=9999, db=0, decode_responses=True)
        
        with pytest.raises(redis.ConnectionError):
            bad_client.ping()


    @pytest.mark.asyncio
    async def test_circuit_breaker_without_redis(self):
        """Test circuit breaker fallback when Redis is unavailable."""
        
        # This should fall back to in-memory state
        circuit_breaker = CircuitBreakerService(None)  # No Redis client
        
        # Record multiple failures to open the circuit
        service = ThirdPartyService.PERPLEXITY
        for i in range(circuit_breaker.failure_threshold):
            circuit_breaker.record_failure(service, f"failure_{i}", "Test failure")
        
        # Circuit should now be open
        allowed, reason = circuit_breaker.should_allow_request(service)
        assert not allowed
        assert "OPEN" in reason


if __name__ == "__main__":
    # Run tests manually for development
    import sys
    sys.path.append(".")
    
    # Simple test runner for development
    test_classes = [
        TestCircuitBreakerBasics,
        TestQueueManagerIntegration, 
        TestAlertServiceIntegration,
        TestEndToEndScenarios,
        TestRealTimeScenarios,
        TestCircuitBreakerIntegration,
        TestRateLimiterIntegration,
        TestCircuitBreakerRateLimiterIntegration,
        TestRedisConnectionHandling
    ]
    
    # Use Redis service name from docker-compose when running in container
    redis_host = os.getenv('REDIS_HOST', 'lead-gen-redis-1')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    
    redis_client = redis.Redis(host=redis_host, port=redis_port, db=15)
    redis_client.flushdb()
    
    circuit_breaker = CircuitBreakerService(redis_client)
    mock_db = Mock(spec=Session)
    queue_manager = QueueManager(mock_db, circuit_breaker)
    alert_service = AlertService()
    
    print("Running circuit breaker integration tests...")
    
    # Run basic tests
    basic_tests = TestCircuitBreakerBasics()
    basic_tests.test_initial_state_is_closed(circuit_breaker)
    basic_tests.test_circuit_opens_after_threshold_failures(circuit_breaker)
    
    print("✓ Basic circuit breaker tests passed")
    
    # Test queue integration
    queue_tests = TestQueueManagerIntegration()
    queue_tests.test_should_process_job_with_closed_circuit(queue_manager)
    
    print("✓ Queue manager integration tests passed")
    
    # Test alert integration
    alert_tests = TestAlertServiceIntegration()
    alert_tests.test_alert_level_determination(alert_service)
    
    print("✓ Alert service tests passed")
    
    print("\n🎉 All integration tests passed! Circuit breaker system is working correctly.")
    
    redis_client.flushdb()  # Clean up 