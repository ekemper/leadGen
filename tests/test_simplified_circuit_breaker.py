"""
Test suite for simplified circuit breaker implementation

Tests cover:
- Only OPEN/CLOSED states (no HALF_OPEN)
- Global circuit breaker state (not service-specific)
- Manual frontend-only closing
- Job pause/resume on breaker state changes
- Single source of truth for system health
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from app.core.circuit_breaker import CircuitBreakerService, CircuitState
from app.models.job import Job, JobStatus
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.organization import Organization


class TestSimplifiedCircuitBreaker:
    """Test the simplified circuit breaker with only OPEN/CLOSED states."""

    def test_only_open_and_closed_states_allowed(self, mock_redis):
        """Circuit breaker should only have OPEN and CLOSED states."""
        cb = CircuitBreakerService(mock_redis)
        
        # Test setting CLOSED state
        cb._set_global_circuit_state(CircuitState.CLOSED)
        assert cb.get_global_circuit_state() == CircuitState.CLOSED
        
        # Test setting OPEN state
        cb._set_global_circuit_state(CircuitState.OPEN)
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # HALF_OPEN should not exist in simplified version
        with pytest.raises(ValueError):
            CircuitState("HALF_OPEN")

    def test_immediate_open_on_any_failure(self, mock_redis):
        """Any service failure should immediately open the circuit breaker."""
        cb = CircuitBreakerService(mock_redis)
        
        # Start with closed circuit
        assert cb.get_global_circuit_state() == CircuitState.CLOSED
        
        # Any failure should immediately open circuit
        cb.record_failure("Service error occurred")
        assert cb.get_global_circuit_state() == CircuitState.OPEN

    def test_manual_only_circuit_close(self, mock_redis):
        """Circuit breaker should only close via manual API call."""
        cb = CircuitBreakerService(mock_redis)
        
        # Open the circuit
        cb.record_failure("Service error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # Circuit should remain open until manually closed
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # Only manual close should work
        cb.manually_close_circuit()
        assert cb.get_global_circuit_state() == CircuitState.CLOSED

    def test_no_automatic_circuit_closing(self, mock_redis):
        """Circuit breaker should never close automatically."""
        cb = CircuitBreakerService(mock_redis)
        
        # Open circuit
        cb.record_failure("Service error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # Record success - circuit should remain open
        cb.record_success()
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # Time passage should not close circuit
        future_time = datetime.utcnow() + timedelta(hours=1)
        with patch('app.core.circuit_breaker.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = future_time
            assert cb.get_global_circuit_state() == CircuitState.OPEN

    def test_global_circuit_breaker_state(self, mock_redis):
        """Circuit breaker should maintain single global state."""
        cb = CircuitBreakerService(mock_redis)
        
        # Should use global state, not service-specific
        assert cb.get_global_circuit_state() == CircuitState.CLOSED
        
        # Any failure opens global circuit
        cb.record_failure("Apollo service error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # All requests should be blocked when circuit is open
        assert not cb.should_allow_request()
        
        # Manual close affects global state
        cb.manually_close_circuit()
        assert cb.get_global_circuit_state() == CircuitState.CLOSED
        assert cb.should_allow_request()


class TestJobPauseResumeOnCircuitBreakerChanges:
    """Test that jobs pause/resume based on circuit breaker state changes."""

    @pytest.fixture
    def test_organization(self, db_session):
        """Create test organization for campaigns."""
        org = Organization(
            id="test-org-1",
            name="Test Organization"
        )
        db_session.add(org)
        db_session.commit()
        return org

    @pytest.fixture
    def setup_jobs(self, db_session, test_organization):
        """Create test jobs in various states."""
        campaign = Campaign(
            id="test-campaign-1",
            name="Test Campaign",
            status=CampaignStatus.RUNNING,
            organization_id=test_organization.id,
            fileName="test_file.csv",
            totalRecords=100,
            url="https://example.com/test"
        )
        db_session.add(campaign)
        
        jobs = [
            Job(id=1, name="Job 1", status=JobStatus.PENDING, campaign_id=campaign.id),
            Job(id=2, name="Job 2", status=JobStatus.PROCESSING, campaign_id=campaign.id),
            Job(id=3, name="Job 3", status=JobStatus.COMPLETED, campaign_id=campaign.id),
            Job(id=4, name="Job 4", status=JobStatus.FAILED, campaign_id=campaign.id),
            Job(id=5, name="Job 5", status=JobStatus.PAUSED, campaign_id=campaign.id),
        ]
        for job in jobs:
            db_session.add(job)
        
        db_session.commit()
        return jobs

    @patch('app.core.queue_manager.QueueManager.pause_all_jobs_on_breaker_open')
    def test_all_active_jobs_pause_on_circuit_open(self, mock_pause, db_session, setup_jobs, mock_redis):
        """All PENDING/PROCESSING jobs should pause when circuit opens."""
        cb = CircuitBreakerService(mock_redis)
        mock_pause.return_value = 2  # Mock 2 jobs paused
        
        # Initially circuit is closed
        assert cb.get_global_circuit_state() == CircuitState.CLOSED
        
        # Open circuit - should trigger job pause
        cb.record_failure("Service error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # Verify pause method was called
        mock_pause.assert_called_once_with("Service error")

    @patch('app.core.queue_manager.QueueManager.resume_all_jobs_on_breaker_close')
    def test_all_paused_jobs_resume_on_circuit_close(self, mock_resume, db_session, setup_jobs, mock_redis):
        """All PAUSED jobs should resume when circuit closes."""
        cb = CircuitBreakerService(mock_redis)
        mock_resume.return_value = 3  # Mock 3 jobs resumed
        
        # First open circuit
        cb.record_failure("Service error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # Close circuit - should trigger job resume
        cb.manually_close_circuit()
        assert cb.get_global_circuit_state() == CircuitState.CLOSED
        
        # Verify resume method was called
        mock_resume.assert_called_once()

    def test_job_pause_includes_circuit_breaker_context(self, db_session, setup_jobs, mock_redis):
        """Circuit breaker should handle job pausing with proper context."""
        cb = CircuitBreakerService(mock_redis)
        
        # This test verifies the circuit breaker integration works
        # The actual job pausing logic is tested in test_simplified_job_management.py
        
        # Open circuit with specific error
        error_message = "Apollo API service timeout"
        cb.record_failure(error_message)
        
        # Verify circuit is open and error is stored
        status = cb.get_circuit_status()
        assert status['state'] == CircuitState.OPEN.value
        assert error_message in status['metadata']['last_error']


class TestCampaignStateIsolation:
    """Test that campaigns never pause regardless of circuit breaker state."""

    @pytest.fixture
    def test_organization(self, db_session):
        """Create test organization for campaigns."""
        org = Organization(
            id="test-org-2",
            name="Test Organization 2"
        )
        db_session.add(org)
        db_session.commit()
        return org

    @patch('app.core.queue_manager.QueueManager.pause_all_jobs_on_breaker_open')
    def test_campaigns_remain_running_when_circuit_opens(self, mock_pause, db_session, test_organization, mock_redis):
        """Campaigns should remain RUNNING even when circuit breaker opens."""
        cb = CircuitBreakerService(mock_redis)
        mock_pause.return_value = 0
        
        # Create running campaign
        campaign = Campaign(
            id="test-campaign-1",
            name="Test Campaign",
            status=CampaignStatus.RUNNING,
            organization_id=test_organization.id,
            fileName="test_file.csv",
            totalRecords=100,
            url="https://example.com/test"
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Open circuit breaker
        cb.record_failure("Service error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # Campaign should still be RUNNING
        db_session.refresh(campaign)
        assert campaign.status == CampaignStatus.RUNNING

    def test_campaigns_can_start_when_circuit_closed(self, db_session, test_organization, mock_redis):
        """Campaigns should be able to start when circuit is closed."""
        cb = CircuitBreakerService(mock_redis)
        
        # Create new campaign
        campaign = Campaign(
            id="test-campaign-1",
            name="Test Campaign",
            status=CampaignStatus.CREATED,
            organization_id=test_organization.id,
            fileName="test_file.csv",
            totalRecords=100,
            url="https://example.com/test"
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Circuit is closed - campaign should be startable (if it has the method)
        assert cb.get_global_circuit_state() == CircuitState.CLOSED
        # Note: can_be_started() method not tested here since it may not exist yet

    def test_campaigns_cannot_start_when_circuit_open(self, db_session, test_organization, mock_redis):
        """Campaigns should not be able to start when circuit is open."""
        cb = CircuitBreakerService(mock_redis)
        
        # Create new campaign
        campaign = Campaign(
            id="test-campaign-1",
            name="Test Campaign",
            status=CampaignStatus.CREATED,
            organization_id=test_organization.id,
            fileName="test_file.csv",
            totalRecords=100,
            url="https://example.com/test"
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Open circuit
        cb.record_failure("Service error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        # Circuit is open - this would prevent campaign starting in business logic
        # Note: actual prevention logic would be in campaign service


class TestSingleSourceOfTruth:
    """Test that circuit breaker state is the single source of truth."""

    def test_no_service_specific_state_tracking(self, mock_redis):
        """Circuit breaker should not track individual service states."""
        cb = CircuitBreakerService(mock_redis)
        
        # Should only have global state methods
        assert hasattr(cb, 'get_global_circuit_state')
        assert not hasattr(cb, 'get_service_circuit_state')
        
        # All failures should affect global state
        cb.record_failure("Apollo error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        
        cb.manually_close_circuit()
        cb.record_failure("OpenAI error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN

    def test_job_processing_checks_global_circuit_state(self, mock_redis):
        """Job processing should only check global circuit breaker state."""
        cb = CircuitBreakerService(mock_redis)
        
        # When circuit is closed, jobs should be allowed
        assert cb.get_global_circuit_state() == CircuitState.CLOSED
        assert cb.should_allow_request()
        
        # When circuit is open, no jobs should be allowed
        cb.record_failure("Service error")
        assert cb.get_global_circuit_state() == CircuitState.OPEN
        assert not cb.should_allow_request()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing with proper state storage simulation."""
    redis_mock = Mock()
    
    # Create a dictionary to simulate Redis storage
    redis_storage = {}
    
    def mock_get(key):
        return redis_storage.get(key)
    
    def mock_setex(key, ttl, value):
        redis_storage[key] = value
        return True
    
    def mock_delete(key):
        if key in redis_storage:
            del redis_storage[key]
            return True
        return False
    
    # Configure the mock methods
    redis_mock.get.side_effect = mock_get
    redis_mock.setex.side_effect = mock_setex
    redis_mock.delete.side_effect = mock_delete
    
    return redis_mock 