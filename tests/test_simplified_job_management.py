"""
Test suite for simplified job management implementation

Tests cover:
- Job pause when circuit breaker opens
- Job resume when circuit breaker closes (with new celery tasks)
- Job state transitions without campaign coupling
- No service-specific job dependencies
- Celery task creation for resumed jobs
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime

from app.core.queue_manager import QueueManager
from app.core.circuit_breaker import CircuitBreakerService, CircuitState
from app.models.job import Job, JobStatus, JobType
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.organization import Organization


class TestJobPauseOnCircuitBreakerOpen:
    """Test that all active jobs pause when circuit breaker opens."""

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
    def setup_mixed_jobs(self, db_session, test_organization):
        """Create jobs in various states for testing pause functionality."""
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
            Job(id=1, name="Pending Job", status=JobStatus.PENDING, 
                job_type=JobType.FETCH_LEADS, campaign_id=campaign.id),
            Job(id=2, name="Processing Job", status=JobStatus.PROCESSING, 
                job_type=JobType.ENRICH_LEAD, campaign_id=campaign.id),
            Job(id=3, name="Completed Job", status=JobStatus.COMPLETED, 
                job_type=JobType.FETCH_LEADS, campaign_id=campaign.id),
            Job(id=4, name="Failed Job", status=JobStatus.FAILED, 
                job_type=JobType.ENRICH_LEAD, campaign_id=campaign.id),
            Job(id=5, name="Already Paused Job", status=JobStatus.PAUSED, 
                job_type=JobType.FETCH_LEADS, campaign_id=campaign.id),
            Job(id=6, name="Cancelled Job", status=JobStatus.CANCELLED, 
                job_type=JobType.CLEANUP_CAMPAIGN, campaign_id=campaign.id),
        ]
        for job in jobs:
            db_session.add(job)
        
        db_session.commit()
        return jobs

    def test_pause_all_active_jobs_on_breaker_open(self, db_session, setup_mixed_jobs, mock_redis):
        """All PENDING/PROCESSING jobs should pause when circuit breaker opens."""
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        # Trigger circuit breaker open
        paused_count = queue_manager.pause_all_jobs_on_breaker_open("Service failure detected")
        
        # Should have paused 2 jobs (PENDING and PROCESSING)
        assert paused_count == 2
        
        # Check job states after pause
        jobs = db_session.query(Job).all()
        job_states = {job.id: job.status for job in jobs}
        
        # PENDING and PROCESSING jobs should be paused
        assert job_states[1] == JobStatus.PAUSED  # Was PENDING
        assert job_states[2] == JobStatus.PAUSED  # Was PROCESSING
        
        # Other states should remain unchanged
        assert job_states[3] == JobStatus.COMPLETED
        assert job_states[4] == JobStatus.FAILED
        assert job_states[5] == JobStatus.PAUSED
        assert job_states[6] == JobStatus.CANCELLED

    def test_pause_includes_circuit_breaker_reason(self, db_session, setup_mixed_jobs, mock_redis):
        """Paused jobs should include reason for circuit breaker pause."""
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        failure_reason = "Apollo API timeout error"
        queue_manager.pause_all_jobs_on_breaker_open(failure_reason)
        
        # Check that paused jobs have proper error context
        paused_jobs = db_session.query(Job).filter(Job.status == JobStatus.PAUSED).all()
        
        # Should be 3 paused jobs (1 original + 2 newly paused)
        assert len(paused_jobs) == 3
        
        # Check the newly paused jobs (jobs 1 and 2)
        for job in paused_jobs:
            if job.id in [1, 2]:  # Jobs that were just paused
                assert job.error is not None
                assert "circuit breaker" in job.error.lower()
                assert "paused" in job.error.lower()
                assert failure_reason in job.error

    def test_no_service_specific_job_filtering(self, db_session, setup_mixed_jobs, mock_redis):
        """All jobs should be affected regardless of job type or service dependency."""
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        # Pause should affect all active jobs regardless of type
        paused_count = queue_manager.pause_all_jobs_on_breaker_open("Global service failure")
        
        # Should pause 2 jobs regardless of type
        assert paused_count == 2
        
        # Get all jobs that were PENDING or PROCESSING
        pending_job = db_session.query(Job).filter_by(id=1).first()  # FETCH_LEADS
        processing_job = db_session.query(Job).filter_by(id=2).first()  # ENRICH_LEAD
        
        # Both should be paused regardless of job type
        assert pending_job.status == JobStatus.PAUSED
        assert processing_job.status == JobStatus.PAUSED


class TestJobResumeOnCircuitBreakerClose:
    """Test that paused jobs resume when circuit breaker closes."""

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

    @pytest.fixture
    def setup_paused_jobs(self, db_session, test_organization):
        """Create paused jobs for testing resume."""
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
            Job(id=1, name="Paused Job 1", status=JobStatus.PAUSED, 
                job_type=JobType.FETCH_LEADS, campaign_id=campaign.id,
                task_id="old_task_1", error="Paused due to circuit breaker open"),
            Job(id=2, name="Paused Job 2", status=JobStatus.PAUSED, 
                job_type=JobType.ENRICH_LEAD, campaign_id=campaign.id,
                task_id="old_task_2", error="Paused due to circuit breaker open"),
            Job(id=3, name="Completed Job", status=JobStatus.COMPLETED, 
                job_type=JobType.FETCH_LEADS, campaign_id=campaign.id),
            Job(id=4, name="Failed Job", status=JobStatus.FAILED, 
                job_type=JobType.ENRICH_LEAD, campaign_id=campaign.id),
        ]
        for job in jobs:
            db_session.add(job)
        
        db_session.commit()
        return jobs

    @patch('app.workers.campaign_tasks.process_job_task')
    def test_resume_all_paused_jobs_on_breaker_close(self, mock_celery_task, db_session, setup_paused_jobs, mock_redis):
        """All PAUSED jobs should resume as PENDING when circuit breaker closes."""
        # Mock celery task creation with unique task IDs
        task_ids = ["new_task_1", "new_task_2"]
        mock_results = [Mock(id=task_id) for task_id in task_ids]
        mock_celery_task.delay.side_effect = mock_results
        
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        # Resume all paused jobs
        resumed_count = queue_manager.resume_all_jobs_on_breaker_close()
        
        # Should have resumed 2 paused jobs
        assert resumed_count == 2
        
        # Check job states after resume
        job1 = db_session.query(Job).filter_by(id=1).first()
        job2 = db_session.query(Job).filter_by(id=2).first()
        
        assert job1.status == JobStatus.PENDING
        assert job2.status == JobStatus.PENDING
        
        # Error should be cleared
        assert job1.error is None
        assert job2.error is None
        
        # Other jobs should remain unchanged
        job3 = db_session.query(Job).filter_by(id=3).first()
        job4 = db_session.query(Job).filter_by(id=4).first()
        
        assert job3.status == JobStatus.COMPLETED
        assert job4.status == JobStatus.FAILED

    @patch('app.workers.campaign_tasks.process_job_task')
    def test_new_celery_tasks_created_for_resumed_jobs(self, mock_celery_task, db_session, setup_paused_jobs, mock_redis):
        """New celery tasks should be created for each resumed job."""
        # Mock task creation with unique IDs
        task_ids = ["new_task_1", "new_task_2"]
        mock_results = [Mock(id=task_id) for task_id in task_ids]
        mock_celery_task.delay.side_effect = mock_results
        
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        # Resume jobs
        resumed_count = queue_manager.resume_all_jobs_on_breaker_close()
        
        # Should have resumed 2 jobs
        assert resumed_count == 2
        
        # Verify celery tasks were created
        assert mock_celery_task.delay.call_count == 2
        
        # Check that job task IDs were updated
        job1 = db_session.query(Job).filter_by(id=1).first()
        job2 = db_session.query(Job).filter_by(id=2).first()
        
        assert job1.task_id in task_ids
        assert job2.task_id in task_ids
        assert job1.task_id != "old_task_1"
        assert job2.task_id != "old_task_2"

    @patch('app.workers.campaign_tasks.process_job_task')
    def test_resume_handles_task_creation_failures(self, mock_celery_task, db_session, setup_paused_jobs, mock_redis):
        """Resume should handle celery task creation failures gracefully."""
        # Mock task creation failure
        mock_celery_task.delay.side_effect = Exception("Celery connection failed")
        
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        # Resume should not crash on task creation failure
        resumed_count = queue_manager.resume_all_jobs_on_breaker_close()
        
        # No jobs should be successfully resumed due to task creation failures
        assert resumed_count == 0
        
        # Jobs should be marked as failed if task creation fails
        job1 = db_session.query(Job).filter_by(id=1).first()
        job2 = db_session.query(Job).filter_by(id=2).first()
        
        assert job1.status == JobStatus.FAILED
        assert job2.status == JobStatus.FAILED
        assert "Failed to create celery task" in job1.error
        assert "Failed to create celery task" in job2.error

    @patch('app.workers.campaign_tasks.process_job_task')
    def test_resume_preserves_job_data_and_context(self, mock_celery_task, db_session, setup_paused_jobs, mock_redis):
        """Resumed jobs should preserve original data and context."""
        # Mock successful task creation with unique task IDs
        task_ids = ["preserve_task_1", "preserve_task_2"]
        mock_results = [Mock(id=task_id) for task_id in task_ids]
        mock_celery_task.delay.side_effect = mock_results
        
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        # Add some data to test jobs
        job1 = db_session.query(Job).filter_by(id=1).first()
        job1.description = "Important job description"
        job1.result = "Partial results before pause"
        db_session.commit()
        
        # Resume jobs
        resumed_count = queue_manager.resume_all_jobs_on_breaker_close()
        
        # Should have resumed jobs
        assert resumed_count == 2
        
        # Check that job data is preserved
        db_session.refresh(job1)
        assert job1.description == "Important job description"
        assert job1.result == "Partial results before pause"
        assert job1.name == "Paused Job 1"
        assert job1.job_type == JobType.FETCH_LEADS


class TestNoServiceSpecificDependencies:
    """Test that jobs no longer depend on specific service availability."""

    def test_job_processing_only_checks_global_circuit_state(self, mock_redis):
        """Jobs should only check global circuit breaker state for processing."""
        queue_manager = QueueManager(redis_client=mock_redis)
        
        # Mock circuit breaker to return closed state
        with patch.object(queue_manager.circuit_breaker, 'should_allow_request') as mock_allow:
            mock_allow.return_value = True
            
            # Should allow job processing when circuit is closed
            assert queue_manager.should_process_job()
            
            # Should not allow when circuit is open
            mock_allow.return_value = False
            assert not queue_manager.should_process_job()

    def test_no_job_type_service_mapping(self, mock_redis):
        """Job types should not be mapped to specific services."""
        queue_manager = QueueManager(redis_client=mock_redis)
        
        # Should not have service-specific logic for job types
        assert not hasattr(queue_manager, 'get_required_services_for_job_type')
        assert not hasattr(queue_manager, 'job_type_service_mapping')
        
        # All job types should be treated equally
        job_types = [JobType.FETCH_LEADS, JobType.ENRICH_LEAD, JobType.CLEANUP_CAMPAIGN]
        
        for job_type in job_types:
            # All should have same processing eligibility based on global circuit state
            with patch.object(queue_manager.circuit_breaker, 'should_allow_request') as mock_allow:
                mock_allow.return_value = True
                assert queue_manager.should_process_job()
                
                mock_allow.return_value = False
                assert not queue_manager.should_process_job()


class TestJobResumeTaskCreationLogic:
    """Test the logic for creating celery tasks when resuming jobs."""

    @pytest.fixture
    def test_organization(self, db_session):
        """Create test organization for campaigns."""
        org = Organization(
            id="test-org-3",
            name="Test Organization 3"
        )
        db_session.add(org)
        db_session.commit()
        return org

    @pytest.fixture
    def setup_diverse_jobs(self, db_session, test_organization):
        """Create jobs with different types and priorities for testing."""
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
            Job(id=1, name="High Priority Fetch", status=JobStatus.PAUSED,
                job_type=JobType.FETCH_LEADS, campaign_id=campaign.id),
            Job(id=2, name="Medium Priority Enrich", status=JobStatus.PAUSED,
                job_type=JobType.ENRICH_LEAD, campaign_id=campaign.id),
            Job(id=3, name="Low Priority Cleanup", status=JobStatus.PAUSED,
                job_type=JobType.CLEANUP_CAMPAIGN, campaign_id=campaign.id),
        ]
        for job in jobs:
            db_session.add(job)
        
        db_session.commit()
        return jobs

    @patch('app.workers.campaign_tasks.process_job_task')
    def test_task_creation_with_correct_parameters(self, mock_celery_task, db_session, setup_diverse_jobs, mock_redis):
        """Celery tasks should be created with correct job parameters."""
        # Mock successful task creation with unique task IDs
        task_ids = ["task_1", "task_2", "task_3"]
        mock_results = [Mock(id=task_id) for task_id in task_ids]
        mock_celery_task.delay.side_effect = mock_results
        
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        # Resume jobs
        resumed_count = queue_manager.resume_all_jobs_on_breaker_close()
        
        # Should have resumed all 3 jobs
        assert resumed_count == 3
        
        # Verify task creation calls
        assert mock_celery_task.delay.call_count == 3
        
        # Check that each job type gets appropriate task creation
        calls = mock_celery_task.delay.call_args_list
        job_ids = [call[1]['job_id'] for call in calls]
        
        assert 1 in job_ids
        assert 2 in job_ids
        assert 3 in job_ids

    @patch('app.workers.campaign_tasks.process_job_task')
    def test_task_creation_retry_logic(self, mock_celery_task, db_session, setup_diverse_jobs, mock_redis):
        """Task creation should have retry logic for transient failures."""
        # Mock intermittent failures - the _create_celery_task_for_job method has retry logic
        # but since we're testing the public interface, we'll test that failures are handled
        mock_celery_task.delay.side_effect = Exception("Transient error")
        
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        # Resume jobs with retry logic
        resumed_count = queue_manager.resume_all_jobs_on_breaker_close()
        
        # Should fail to resume due to task creation failures
        assert resumed_count == 0
        
        # Verify multiple retry attempts were made (3 retries per job * 3 jobs)
        assert mock_celery_task.delay.call_count >= 9  # At least 3 attempts per job

    @patch('app.workers.campaign_tasks.process_job_task')
    def test_comprehensive_error_handling_and_logging(self, mock_celery_task, db_session, setup_diverse_jobs, mock_redis):
        """Resume process should have comprehensive error handling and logging."""
        mock_celery_task.delay.side_effect = Exception("Critical celery failure")
        
        queue_manager = QueueManager(redis_client=mock_redis, db=db_session)
        
        with patch('app.core.queue_manager.logger') as mock_logger:
            # Resume should handle errors gracefully
            resumed_count = queue_manager.resume_all_jobs_on_breaker_close()
            
            # Should not have resumed any jobs due to failures
            assert resumed_count == 0
            
            # Should log errors appropriately
            assert mock_logger.warning.called or mock_logger.error.called


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = Mock()
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.delete.return_value = True
    return redis_mock


@pytest.fixture
def mock_circuit_breaker():
    """Mock circuit breaker for testing."""
    cb_mock = Mock()
    cb_mock.get_global_circuit_state.return_value = CircuitState.CLOSED
    cb_mock.should_allow_request.return_value = True
    return cb_mock 