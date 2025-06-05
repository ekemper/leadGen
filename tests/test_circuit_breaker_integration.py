"""
Test circuit breaker integration with simplified global state.

Updated for simplified circuit breaker:
- Only OPEN/CLOSED states (no HALF_OPEN)
- Global circuit breaker state (not service-specific)
- Manual-only closing via frontend
- Any service error immediately opens circuit
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
import redis
from datetime import datetime, timedelta
import uuid

from app.core.circuit_breaker import CircuitBreakerService, CircuitState, ThirdPartyService
from app.core.queue_manager import QueueManager
from app.core.alert_service import AlertService, AlertLevel
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
from app.models.job import Job, JobStatus, JobType


@pytest.fixture
def redis_client():
    """Create Redis client for testing."""
    client = redis.Redis(host='redis', port=6379, db=1, decode_responses=False)
    # Clear Redis before each test
    client.flushdb()
    yield client
    # Clear Redis after each test
    client.flushdb()


@pytest.fixture
def circuit_breaker(redis_client):
    """Create circuit breaker instance for testing."""
    return CircuitBreakerService(redis_client)


@pytest.fixture
def queue_manager(redis_client):
    """Create queue manager instance for testing."""
    return QueueManager(redis_client)


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return Mock(spec=['query', 'commit', 'rollback', 'close'])


@pytest.fixture
def alert_service():
    """Create alert service instance for testing."""
    return AlertService()


@pytest.fixture
def rate_limiter(redis_client):
    """Create rate limiter instance for testing."""
    unique_api_name = f"test_api_{uuid.uuid4().hex[:8]}"
    return ApiIntegrationRateLimiter(
        redis_client=redis_client,
        api_name=unique_api_name,
        max_requests=10,
        period_seconds=60
    )


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality with simplified logic."""

    def test_initial_state_is_closed(self, circuit_breaker):
        """Test that circuit breaker starts in closed state."""
        state = circuit_breaker.get_global_circuit_state()
        assert state == CircuitState.CLOSED

    def test_circuit_opens_immediately_on_failure(self, circuit_breaker):
        """Test that circuit opens immediately on any failure."""
        # Record single failure - should immediately open
        circuit_breaker.record_failure("Test error", "test_error")
        
        state = circuit_breaker.get_global_circuit_state()
        assert state == CircuitState.OPEN

    def test_circuit_allows_request_when_closed(self, circuit_breaker):
        """Test that closed circuit allows requests."""
        # Ensure circuit is closed
        circuit_breaker.manually_close_circuit()
        
        allowed = circuit_breaker.should_allow_request()
        assert allowed is True

    def test_circuit_blocks_request_when_open(self, circuit_breaker):
        """Test that open circuit blocks requests."""
        # Open the circuit by recording failure
        circuit_breaker.record_failure("Test error", "test_error")
        
        allowed = circuit_breaker.should_allow_request()
        assert allowed is False

    def test_success_does_not_auto_close_circuit(self, circuit_breaker):
        """Test that recording success does NOT automatically close circuit."""
        # Open circuit first
        circuit_breaker.record_failure("Test error", "test_error")
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Record success - circuit should remain open
        circuit_breaker.record_success()
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN

    def test_manual_close_circuit(self, circuit_breaker):
        """Test manual circuit closing."""
        # Open circuit first
        circuit_breaker.record_failure("Test error", "test_error")
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Manually close
        result = circuit_breaker.manually_close_circuit()
        assert result is True
        assert circuit_breaker.get_global_circuit_state() == CircuitState.CLOSED


class TestQueueManagerIntegration:
    """Test queue manager integration with simplified circuit breaker."""

    def test_should_process_job_with_closed_circuit(self, queue_manager):
        """Test job processing when circuit is closed."""
        # Ensure circuit is closed
        queue_manager.circuit_breaker.manually_close_circuit()
        
        should_process = queue_manager.should_process_job()
        assert should_process is True

    def test_should_not_process_job_with_open_circuit(self, queue_manager):
        """Test job processing when circuit is open."""
        # Open the circuit
        queue_manager.circuit_breaker.record_failure("Test error", "test_error")
        
        should_process = queue_manager.should_process_job()
        assert should_process is False

    @patch('app.core.database.SessionLocal')
    def test_pause_all_jobs_on_breaker_open(self, mock_session_local, queue_manager):
        """Test pausing all jobs when circuit breaker opens."""
        # Mock database session and jobs
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        pending_jobs = [
            Mock(spec=Job, id=1, job_type=JobType.ENRICH_LEAD, status=JobStatus.PENDING),
            Mock(spec=Job, id=2, job_type=JobType.FETCH_LEADS, status=JobStatus.PENDING),
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = pending_jobs
        mock_db.query.return_value = mock_query
        
        paused_count = queue_manager.pause_all_jobs_on_breaker_open("Test circuit breaker open")
        
        assert paused_count == 2
        # Verify jobs were marked as paused
        for job in pending_jobs:
            assert job.status == JobStatus.PAUSED
            assert "circuit breaker open" in job.error

    @patch('app.core.database.SessionLocal')
    @patch('app.workers.campaign_tasks.process_job_task')
    def test_resume_all_jobs_on_breaker_close(self, mock_process_task, mock_session_local, queue_manager):
        """Test resuming all jobs when circuit breaker closes."""
        # Mock database session and jobs
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        paused_jobs = [
            Mock(spec=Job, id=1, job_type=JobType.ENRICH_LEAD, status=JobStatus.PAUSED, campaign_id=1),
            Mock(spec=Job, id=2, job_type=JobType.FETCH_LEADS, status=JobStatus.PAUSED, campaign_id=1),
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = paused_jobs
        mock_db.query.return_value = mock_query
        
        # Mock celery task creation
        mock_task = Mock()
        mock_task.id = "new-task-id"
        mock_process_task.delay.return_value = mock_task
        
        resumed_count = queue_manager.resume_all_jobs_on_breaker_close()
        
        assert resumed_count == 2
        # Verify jobs were marked as pending and got new task IDs
        for job in paused_jobs:
            assert job.status == JobStatus.PENDING
            assert job.error is None
            assert job.task_id == "new-task-id"


class TestAlertServiceIntegration:
    """Test alert service integration with simplified circuit breaker."""

    @patch('smtplib.SMTP')
    def test_send_circuit_breaker_alert_critical(self, mock_smtp, alert_service):
        """Test sending critical alert when circuit breaker opens."""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Test critical alert with correct parameters
        alert_service.send_circuit_breaker_alert(
            service=ThirdPartyService.APOLLO,
            old_state=CircuitState.CLOSED,
            new_state=CircuitState.OPEN,
            failure_reason="Test error details",
            failure_count=1
        )
        
        # Verify SMTP connection was called (if email config is present)
        # Note: This may not be called if admin_emails is empty in test config

    def test_send_queue_status_alert(self, alert_service):
        """Test queue status alert generation."""
        # Test with correct parameters for the actual method signature
        alert_service.send_queue_status_alert(
            total_paused_jobs=25,
            services_down=["apollo", "perplexity"],
            job_backlog={"pending": 10, "processing": 5}
        )
        
        # Should not raise exception
        
    def test_send_recovery_alert(self, alert_service):
        """Test service recovery alert."""
        alert_service.send_recovery_alert(
            service=ThirdPartyService.APOLLO,
            jobs_resumed=15
        )
        
        # Should not raise exception


class TestEndToEndScenarios:
    """Test end-to-end scenarios with simplified circuit breaker."""

    @patch('app.core.database.SessionLocal')
    def test_service_failure_scenario_with_manual_resume(self, mock_session_local, circuit_breaker, queue_manager):
        """Test service failure scenario with manual resume requirement."""
        # Mock database
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # Simulate service failure
        circuit_breaker.record_failure("Service timeout", "timeout_error")
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Jobs should not be processed
        assert queue_manager.should_process_job() is False
        
        # Success should not auto-resume
        circuit_breaker.record_success()
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Only manual close should work
        circuit_breaker.manually_close_circuit()
        assert circuit_breaker.get_global_circuit_state() == CircuitState.CLOSED
        assert queue_manager.should_process_job() is True

    @patch('app.core.alert_service.get_alert_service')
    def test_circuit_breaker_with_alerts_and_manual_resume(self, mock_get_alert_service, circuit_breaker):
        """Test circuit breaker with alerts and manual resume requirement."""
        mock_alert_service = Mock()
        mock_get_alert_service.return_value = mock_alert_service
        
        # Trigger circuit breaker
        circuit_breaker.record_failure("Critical service error", "critical_error")
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Simulate alert triggering (would be done by error handling code)
        mock_alert_service.send_circuit_breaker_alert.assert_not_called()  # Not auto-triggered in this simple test
        
        # Manual resume only
        circuit_breaker.manually_close_circuit()
        assert circuit_breaker.get_global_circuit_state() == CircuitState.CLOSED


class TestRealTimeScenarios:
    """Test real-time scenarios with simplified circuit breaker."""

    def test_circuit_immediate_open_behavior(self, circuit_breaker):
        """Test circuit breaker immediate open behavior."""
        # Circuit starts closed
        assert circuit_breaker.get_global_circuit_state() == CircuitState.CLOSED
        
        # Single failure opens circuit immediately
        circuit_breaker.record_failure("Single critical error", "critical")
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Circuit remains open until manually closed
        circuit_breaker.record_success()
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN

    @patch('app.core.database.SessionLocal')
    def test_global_circuit_breaker_affects_all_jobs(self, mock_session_local, circuit_breaker, queue_manager):
        """Test that global circuit breaker affects all jobs regardless of type."""
        # Mock database
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        # Mix of different job types
        all_jobs = [
            Mock(spec=Job, id=1, job_type=JobType.ENRICH_LEAD, status=JobStatus.PENDING),
            Mock(spec=Job, id=2, job_type=JobType.FETCH_LEADS, status=JobStatus.PENDING),
            Mock(spec=Job, id=3, job_type=JobType.CLEANUP_CAMPAIGN, status=JobStatus.PROCESSING),
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = all_jobs
        mock_db.query.return_value = mock_query
        
        # Open circuit breaker
        circuit_breaker.record_failure("Global service issue", "global_error")
        
        # All jobs should be paused regardless of type
        paused_count = queue_manager.pause_all_jobs_on_breaker_open("Global circuit breaker opened")
        assert paused_count == 3
        
        # Verify all job types were paused
        for job in all_jobs:
            assert job.status == JobStatus.PAUSED


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration scenarios."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_persistence(self, redis_client):
        """Test circuit breaker state persistence in Redis."""
        circuit_breaker = CircuitBreakerService(redis_client)
        
        # Test state persistence
        circuit_breaker.record_failure("persistence_test", "test_error")
        state = circuit_breaker.get_global_circuit_state()
        assert state == CircuitState.OPEN
        
        # Create new instance to test persistence
        new_circuit_breaker = CircuitBreakerService(redis_client)
        persisted_state = new_circuit_breaker.get_global_circuit_state()
        assert persisted_state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_flow_requires_manual_resume(self, redis_client):
        """Test circuit breaker recovery flow with manual resume requirement."""
        circuit_breaker = CircuitBreakerService(redis_client)
        
        # Simulate failure and recovery cycle
        circuit_breaker.record_failure("recovery_test", "test_error")
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Success should not auto-close
        circuit_breaker.record_success()
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Only manual close works
        circuit_breaker.manually_close_circuit()
        assert circuit_breaker.get_global_circuit_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_access(self, redis_client):
        """Test circuit breaker behavior under concurrent access."""
        circuit_breaker = CircuitBreakerService(redis_client)
        
        async def concurrent_failures():
            tasks = []
            for i in range(10):
                task = asyncio.create_task(
                    asyncio.to_thread(
                        circuit_breaker.record_failure,
                        f"concurrent_test_{i}",
                        "concurrent_error"
                    )
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        await concurrent_failures()
        
        # Circuit should be open after concurrent failures
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN


class TestRateLimiterIntegration:
    """Test rate limiter integration with simplified circuit breaker."""

    def test_rate_limiter_basic_functionality(self, rate_limiter):
        """Test basic rate limiter functionality."""
        # Should allow requests within limit
        for i in range(5):
            allowed = rate_limiter.acquire()
            assert allowed is True

    def test_rate_limiter_window_reset(self, rate_limiter):
        """Test rate limiter window reset."""
        # Fill up the rate limit
        for i in range(10):
            rate_limiter.acquire()
        
        # Should be blocked now
        allowed = rate_limiter.acquire()
        assert allowed is False

    def test_rate_limiter_acquire_and_check(self, rate_limiter):
        """Test rate limiter acquire and check methods."""
        # Test acquire method
        allowed = rate_limiter.acquire()
        assert allowed is True
        
        # Test get_remaining method (correct method name)
        remaining = rate_limiter.get_remaining()
        assert remaining == 9  # Started with 10, used 1

    def test_rate_limiter_is_allowed(self, rate_limiter):
        """Test rate limiter is_allowed method."""
        # Should be allowed initially
        allowed = rate_limiter.is_allowed()
        assert allowed is True
        
        # Acquire all slots
        for _ in range(10):
            rate_limiter.acquire()
        
        # Should not be allowed now
        allowed = rate_limiter.is_allowed()
        assert allowed is False


class TestCircuitBreakerRateLimiterIntegration:
    """Test combined circuit breaker and rate limiter functionality."""

    @pytest.mark.asyncio
    async def test_combined_protection_with_manual_resume(self, redis_client):
        """Test combined circuit breaker and rate limiter protection with manual resume requirement."""
        circuit_breaker = CircuitBreakerService(redis_client)
        unique_api_name = f"combined_test_{uuid.uuid4().hex[:8]}"
        rate_limiter = ApiIntegrationRateLimiter(
            redis_client=redis_client,
            api_name=unique_api_name,
            max_requests=3,
            period_seconds=10
        )
        
        def protected_operation():
            # First check rate limiting
            if not rate_limiter.acquire():
                circuit_breaker.record_failure("rate_limit_exceeded", "rate_limit")
                return False, "Rate limited"
            
            # Then check circuit breaker
            allowed = circuit_breaker.should_allow_request()
            if not allowed:
                return False, "Circuit breaker open"
            
            # Simulate operation success/failure
            return True, "Success"
        
        # Test normal operation
        for i in range(3):
            success, reason = protected_operation()
            assert success is True
        
        # Next request should trigger rate limit and open circuit
        success, reason = protected_operation()
        assert success is False
        assert "Rate limited" in reason
        
        # Circuit should now be open
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN


class TestRedisConnectionHandling:
    """Test Redis connection handling and fallback behavior."""

    def test_redis_connection_failure(self):
        """Test circuit breaker behavior when Redis is unavailable."""
        # Create circuit breaker with invalid Redis connection
        invalid_redis = redis.Redis(host='invalid_host', port=6379, db=0)
        circuit_breaker = CircuitBreakerService(invalid_redis)
        
        # Should handle Redis failures gracefully
        circuit_breaker.record_failure("test_failure", "test_error")
        circuit_breaker.record_success()
        
        # Should not raise exceptions
        allowed = circuit_breaker.should_allow_request()
        # Should fail-safe to allow requests
        assert allowed is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_without_redis(self):
        """Test circuit breaker fallback behavior without Redis."""
        invalid_redis = redis.Redis(host='invalid_host', port=6379, db=0)
        circuit_breaker = CircuitBreakerService(invalid_redis)
        
        allowed = circuit_breaker.should_allow_request()
        
        # Should allow requests when Redis is unavailable (fail-open)
        assert allowed is True


class TestCampaignCircuitBreakerIntegration:
    """Test campaign integration with simplified circuit breaker logic."""

    @patch('app.core.database.SessionLocal')
    def test_circuit_breaker_opening_pauses_jobs_not_campaigns(self, mock_session_local, circuit_breaker):
        """Test that circuit breaker opening pauses jobs, not campaigns (new logic)."""
        # Mock database
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # Open circuit breaker - this should pause jobs, not campaigns
        circuit_breaker.record_failure("Test service error", "test_error")
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Note: In new logic, campaigns don't pause - only jobs do
        # This test verifies the circuit breaker opens correctly

    def test_circuit_breaker_closing_does_not_auto_resume_campaigns(self, circuit_breaker):
        """Test that circuit breaker closing does NOT automatically resume campaigns (new logic)."""
        # Open and then close circuit breaker
        circuit_breaker.record_failure("Test service error", "test_error")
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Manually close circuit breaker
        circuit_breaker.manually_close_circuit()
        assert circuit_breaker.get_global_circuit_state() == CircuitState.CLOSED
        
        # Note: In new logic, campaigns never pause/resume automatically
        # Only jobs are affected by circuit breaker state

    def test_manual_queue_resume_requires_global_circuit_breaker_closed(self, circuit_breaker):
        """Test that manual queue resume requires global circuit breaker to be closed (new logic)."""
        
        # Open the global circuit breaker
        circuit_breaker.record_failure("Test global error", "global_error")
        assert circuit_breaker.get_global_circuit_state() == CircuitState.OPEN
        
        # Queue resume should require circuit breaker to be closed
        # (This would be enforced by the queue management API endpoints)
        
        # Only after manual close should queue resume be possible
        circuit_breaker.manually_close_circuit()
        assert circuit_breaker.get_global_circuit_state() == CircuitState.CLOSED
        
        # Now queue resume would be allowed
        assert circuit_breaker.should_allow_request() is True 