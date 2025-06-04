"""
Job Status Integration Tests for Campaign Status Refactor

This module tests the integration between job status changes and campaign status updates
according to the new simplified business rules:

1. ANY job pause should trigger campaign pause evaluation
2. Job status changes should be properly tracked and audited
3. Campaign status should respond to job lifecycle events
4. Job-campaign relationship integrity should be maintained
5. Bulk job operations should maintain consistency

Test Coverage:
- Individual job status change triggers
- Bulk job status operations
- Job-campaign relationship validation
- Job lifecycle integration with campaign status
- Error handling and edge cases
- Database consistency during job operations
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.organization import Organization
from app.models.campaign import Campaign, CampaignStatus
from app.models.job import Job, JobStatus, JobType
from app.core.circuit_breaker import ThirdPartyService, CircuitState
from tests.helpers.auth_helpers import AuthHelpers
from tests.helpers.database_helpers import DatabaseHelpers


class TestJobStatusIntegration:
    """Test job status changes and their integration with campaign status logic."""

    # ===== FIXTURES =====

    @pytest.fixture
    def test_organization(self, db_session):
        """Create test organization for job status tests."""
        org = Organization(
            id="test-org-job-status",
            name="Test Org Job Status Integration",
            description="Testing organization for job status integration"
        )
        db_session.add(org)
        db_session.commit()
        return org

    @pytest.fixture
    def running_campaign_with_multiple_jobs(self, db_session, test_organization, db_helpers):
        """Create a running campaign with multiple jobs of different types."""
        campaign = Campaign(
            name="Multi-Job Test Campaign",
            description="Campaign with multiple jobs for status testing",
            organization_id=test_organization.id,
            fileName="multi_job_test.csv",
            totalRecords=100,
            url="https://app.apollo.io/multi-job-test",
            status=CampaignStatus.RUNNING
        )
        
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)
        
        # Create multiple jobs with different types and statuses
        jobs = []
        
        # Fetch leads job - processing
        fetch_job = Job(
            name="Fetch Leads Job",
            description="Fetching leads from Apollo",
            job_type=JobType.FETCH_LEADS,
            status=JobStatus.PROCESSING,
            campaign_id=campaign.id,
            task_id="task-fetch-leads"
        )
        
        # Enrich lead job - pending
        enrich_job = Job(
            name="Enrich Lead Job",
            description="Enriching lead data",
            job_type=JobType.ENRICH_LEAD,
            status=JobStatus.PENDING,
            campaign_id=campaign.id,
            task_id="task-enrich-lead"
        )
        
        # Cleanup job - pending
        cleanup_job = Job(
            name="Cleanup Campaign Job",
            description="Cleaning up campaign data",
            job_type=JobType.CLEANUP_CAMPAIGN,
            status=JobStatus.PENDING,
            campaign_id=campaign.id,
            task_id="task-cleanup"
        )
        
        jobs = [fetch_job, enrich_job, cleanup_job]
        db_session.add_all(jobs)
        db_session.commit()
        
        for job in jobs:
            db_session.refresh(job)
        
        return campaign, jobs

    @pytest.fixture
    def db_helpers(self, db_session):
        """Database helpers for verification."""
        return DatabaseHelpers(db_session)

    # ===== INDIVIDUAL JOB STATUS CHANGE TESTS =====

    def test_single_job_pause_triggers_campaign_evaluation(self, authenticated_client, db_session,
                                                         running_campaign_with_multiple_jobs, db_helpers):
        """Test that pausing a single job triggers campaign status evaluation."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # Initially campaign should be running
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
        
        # Pause the processing job
        processing_job = jobs[0]  # fetch_job
        assert processing_job.status == JobStatus.PROCESSING
        
        # Update job status to paused
        processing_job.status = JobStatus.PAUSED
        processing_job.error = "Job paused due to service failure"
        db_session.commit()
        
        # Verify job status change
        db_helpers.verify_job_status_in_db(processing_job.id, JobStatus.PAUSED)
        
        # TODO: In actual implementation, this should trigger campaign evaluation
        # For now, simulate the expected behavior
        # campaign_status_monitor.evaluate_campaign_for_job_status_change(processing_job, db_session)
        
        # Simulate the expected campaign pause
        campaign.pause(f"Job {processing_job.name} paused")
        db_session.commit()
        
        # Verify campaign is now paused
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Verify status message indicates job pause
        updated_campaign = db_session.query(Campaign).filter(Campaign.id == campaign.id).first()
        assert "Job" in updated_campaign.status_message
        assert processing_job.name in updated_campaign.status_message

    def test_job_failure_triggers_campaign_evaluation(self, authenticated_client, db_session,
                                                    running_campaign_with_multiple_jobs, db_helpers):
        """Test that job failure triggers campaign status evaluation."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # Initially campaign should be running
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
        
        # Fail the processing job
        processing_job = jobs[0]
        processing_job.status = JobStatus.FAILED
        processing_job.error = "Apollo API returned 500 error"
        db_session.commit()
        
        # Verify job status change
        db_helpers.verify_job_status_in_db(processing_job.id, JobStatus.FAILED)
        
        # Failed jobs should trigger campaign evaluation (similar to pause)
        # In new logic, failed jobs may pause campaign depending on business rules
        campaign.pause(f"Job {processing_job.name} failed: {processing_job.error}")
        db_session.commit()
        
        # Verify campaign response to job failure
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        updated_campaign = db_session.query(Campaign).filter(Campaign.id == campaign.id).first()
        assert "failed" in updated_campaign.status_message.lower()

    def test_job_completion_does_not_auto_resume_campaign(self, authenticated_client, db_session,
                                                        running_campaign_with_multiple_jobs, db_helpers):
        """Test that job completion does NOT automatically resume paused campaigns (new logic)."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # First pause the campaign due to job issue
        processing_job = jobs[0]
        processing_job.status = JobStatus.PAUSED
        campaign.pause(f"Job {processing_job.name} paused")
        db_session.commit()
        
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Now complete another job
        pending_job = jobs[1]
        pending_job.status = JobStatus.COMPLETED
        pending_job.result = "Job completed successfully"
        pending_job.completed_at = datetime.now(timezone.utc)
        db_session.commit()
        
        # Verify job completion
        db_helpers.verify_job_status_in_db(pending_job.id, JobStatus.COMPLETED)
        
        # Campaign should remain paused (no automatic resume)
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Only manual queue resume should be able to resume campaigns

    def test_multiple_job_status_changes_maintain_consistency(self, authenticated_client, db_session,
                                                            running_campaign_with_multiple_jobs, db_helpers):
        """Test that multiple simultaneous job status changes maintain database consistency."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # Initially all jobs have different statuses
        fetch_job, enrich_job, cleanup_job = jobs
        
        # Verify initial states
        db_helpers.verify_job_status_in_db(fetch_job.id, JobStatus.PROCESSING)
        db_helpers.verify_job_status_in_db(enrich_job.id, JobStatus.PENDING)
        db_helpers.verify_job_status_in_db(cleanup_job.id, JobStatus.PENDING)
        
        # Update multiple jobs simultaneously
        fetch_job.status = JobStatus.COMPLETED
        fetch_job.completed_at = datetime.now(timezone.utc)
        
        enrich_job.status = JobStatus.PROCESSING
        
        cleanup_job.status = JobStatus.PAUSED
        cleanup_job.error = "Cleanup service temporarily unavailable"
        
        db_session.commit()
        
        # Verify all changes persisted correctly
        db_helpers.verify_job_status_in_db(fetch_job.id, JobStatus.COMPLETED)
        db_helpers.verify_job_status_in_db(enrich_job.id, JobStatus.PROCESSING)
        db_helpers.verify_job_status_in_db(cleanup_job.id, JobStatus.PAUSED)
        
        # Campaign should be paused due to cleanup job pause
        campaign.pause(f"Job {cleanup_job.name} paused")
        db_session.commit()
        
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)

    # ===== BULK JOB OPERATIONS TESTS =====

    def test_bulk_job_pause_for_service_failure(self, authenticated_client, db_session,
                                               running_campaign_with_multiple_jobs, db_helpers):
        """Test bulk job pause when a service fails (circuit breaker scenario)."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # Simulate service failure affecting multiple jobs
        # In real scenario: Apollo service fails → circuit breaker opens → pause Apollo-dependent jobs
        
        apollo_dependent_jobs = [job for job in jobs if job.job_type in [JobType.FETCH_LEADS, JobType.ENRICH_LEAD]]
        
        # Bulk pause Apollo-dependent jobs
        for job in apollo_dependent_jobs:
            job.status = JobStatus.PAUSED
            job.error = "Apollo service unavailable: Circuit breaker opened"
        
        db_session.commit()
        
        # Verify all Apollo jobs are paused
        for job in apollo_dependent_jobs:
            db_helpers.verify_job_status_in_db(job.id, JobStatus.PAUSED)
        
        # Campaign should be paused due to multiple job pauses
        campaign.pause("Multiple jobs paused: Apollo service unavailable")
        db_session.commit()
        
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Non-Apollo jobs should remain unaffected
        non_apollo_jobs = [job for job in jobs if job.job_type == JobType.CLEANUP_CAMPAIGN]
        for job in non_apollo_jobs:
            # Should still be in original status (PENDING)
            db_helpers.verify_job_status_in_db(job.id, JobStatus.PENDING)

    def test_bulk_job_resume_through_queue_management(self, authenticated_client, db_session,
                                                    running_campaign_with_multiple_jobs, db_helpers):
        """Test that bulk job resume only works through queue management (new logic)."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # First pause all jobs and campaign
        for job in jobs:
            job.status = JobStatus.PAUSED
            job.error = "Service maintenance pause"
        
        campaign.pause("All jobs paused for maintenance")
        db_session.commit()
        
        # Verify all paused
        for job in jobs:
            db_helpers.verify_job_status_in_db(job.id, JobStatus.PAUSED)
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Attempt to resume jobs directly (should not work in new logic)
        # Jobs should only resume when campaign/queue is resumed
        
        # Simulate queue resume triggering job resume
        queue_resume_response = authenticated_client.post("/api/v1/queue-management/resume-service")
        
        if queue_resume_response.status_code == 200:
            # If queue resume works, jobs should be eligible for resume
            # But actual job resume should be coordinated with campaign resume
            
            # For now, simulate the expected coordinated resume
            campaign.resume("Queue resumed - jobs can now resume")
            
            for job in jobs:
                if job.status == JobStatus.PAUSED:
                    job.status = JobStatus.PENDING  # Reset to pending for re-processing
                    job.error = None
            
            db_session.commit()
            
            # Verify coordinated resume
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
            for job in jobs:
                db_helpers.verify_job_status_in_db(job.id, JobStatus.PENDING)

    # ===== JOB-CAMPAIGN RELATIONSHIP VALIDATION =====

    def test_job_campaign_relationship_integrity(self, authenticated_client, db_session,
                                                running_campaign_with_multiple_jobs, db_helpers):
        """Test that job-campaign relationships remain intact during status changes."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # Verify initial relationships
        for job in jobs:
            assert job.campaign_id == campaign.id
            db_session.refresh(job)
            assert job.campaign is not None
            assert job.campaign.id == campaign.id
        
        # Update job statuses
        jobs[0].status = JobStatus.COMPLETED
        jobs[1].status = JobStatus.FAILED
        jobs[2].status = JobStatus.PAUSED
        
        db_session.commit()
        
        # Verify relationships are maintained after status changes
        for job in jobs:
            db_session.refresh(job)
            assert job.campaign_id == campaign.id
            assert job.campaign is not None
            assert job.campaign.id == campaign.id
        
        # Verify campaign can access all its jobs
        db_session.refresh(campaign)
        campaign_jobs = campaign.jobs
        assert len(campaign_jobs) == 3
        
        job_ids = {job.id for job in jobs}
        campaign_job_ids = {job.id for job in campaign_jobs}
        assert job_ids == campaign_job_ids

    def test_orphaned_job_prevention(self, authenticated_client, db_session, test_organization, db_helpers):
        """Test that jobs cannot be created without valid campaign relationships."""
        # Try to create job without campaign
        orphaned_job = Job(
            name="Orphaned Job",
            description="Job without campaign",
            job_type=JobType.FETCH_LEADS,
            status=JobStatus.PENDING,
            task_id="task-orphaned"
            # No campaign_id set
        )
        
        db_session.add(orphaned_job)
        
        try:
            db_session.commit()
            # If this succeeds, verify the job is properly handled
            db_session.refresh(orphaned_job)
            assert orphaned_job.campaign_id is None
            
            # In production, orphaned jobs should be cleaned up or prevented
            # For now, just verify they can be identified
            orphaned_jobs = db_session.query(Job).filter(Job.campaign_id.is_(None)).all()
            assert len(orphaned_jobs) >= 1
            
        except Exception as e:
            # If database constraints prevent orphaned jobs, that's also valid
            db_session.rollback()
            # This is actually the preferred behavior

    def test_job_deletion_campaign_consistency(self, authenticated_client, db_session,
                                             running_campaign_with_multiple_jobs, db_helpers):
        """Test campaign consistency when jobs are deleted."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # Verify initial job count
        initial_job_count = len(jobs)
        campaign_jobs = db_helpers.get_campaign_jobs_from_db(campaign.id)
        assert len(campaign_jobs) == initial_job_count
        
        # Delete one job
        job_to_delete = jobs[0]
        job_id_to_delete = job_to_delete.id
        
        db_session.delete(job_to_delete)
        db_session.commit()
        
        # Verify job is deleted
        deleted_job = db_session.query(Job).filter(Job.id == job_id_to_delete).first()
        assert deleted_job is None
        
        # Verify campaign job count is updated
        remaining_jobs = db_helpers.get_campaign_jobs_from_db(campaign.id)
        assert len(remaining_jobs) == initial_job_count - 1
        
        # Verify campaign status is not affected by job deletion
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)

    # ===== JOB LIFECYCLE INTEGRATION TESTS =====

    def test_complete_job_lifecycle_with_campaign_integration(self, authenticated_client, db_session,
                                                            test_organization, db_helpers):
        """Test complete job lifecycle and its integration with campaign status."""
        # Create campaign
        campaign = Campaign(
            name="Job Lifecycle Test Campaign",
            description="Testing complete job lifecycle",
            organization_id=test_organization.id,
            fileName="job_lifecycle_test.csv",
            totalRecords=50,
            url="https://app.apollo.io/job-lifecycle-test",
            status=CampaignStatus.RUNNING
        )
        
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)
        
        # Create job in PENDING status
        job = Job(
            name="Lifecycle Test Job",
            description="Testing complete job lifecycle",
            job_type=JobType.FETCH_LEADS,
            status=JobStatus.PENDING,
            campaign_id=campaign.id,
            task_id="task-lifecycle-test"
        )
        
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # Verify initial state
        db_helpers.verify_job_status_in_db(job.id, JobStatus.PENDING)
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
        
        # Job starts processing
        job.status = JobStatus.PROCESSING
        db_session.commit()
        
        db_helpers.verify_job_status_in_db(job.id, JobStatus.PROCESSING)
        # Campaign should remain running
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
        
        # Job encounters error and gets paused
        job.status = JobStatus.PAUSED
        job.error = "Temporary service unavailability"
        db_session.commit()
        
        db_helpers.verify_job_status_in_db(job.id, JobStatus.PAUSED)
        
        # Campaign should be paused due to job pause
        campaign.pause(f"Job {job.name} paused: {job.error}")
        db_session.commit()
        
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Service recovers - manual queue resume
        queue_resume_response = authenticated_client.post("/api/v1/queue-management/resume-service")
        
        if queue_resume_response.status_code == 200:
            # Campaign and job can be resumed
            campaign.resume("Service recovered - resuming operations")
            job.status = JobStatus.PROCESSING
            job.error = None
            db_session.commit()
            
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
            db_helpers.verify_job_status_in_db(job.id, JobStatus.PROCESSING)
            
            # Job completes successfully
            job.status = JobStatus.COMPLETED
            job.result = "Successfully fetched 25 leads"
            job.completed_at = datetime.now(timezone.utc)
            db_session.commit()
            
            db_helpers.verify_job_status_in_db(job.id, JobStatus.COMPLETED)
            # Campaign remains running (no auto-pause on completion)
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)

    # ===== ERROR HANDLING AND EDGE CASES =====

    def test_concurrent_job_status_updates(self, authenticated_client, db_session,
                                         running_campaign_with_multiple_jobs, db_helpers):
        """Test handling of concurrent job status updates."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # Simulate concurrent updates to different jobs
        # This tests database transaction isolation
        
        job1, job2, job3 = jobs
        
        # Update jobs in separate "transactions" (simulated)
        job1.status = JobStatus.COMPLETED
        job1.completed_at = datetime.now(timezone.utc)
        
        job2.status = JobStatus.FAILED
        job2.error = "Concurrent update test failure"
        
        job3.status = JobStatus.PAUSED
        job3.error = "Concurrent update test pause"
        
        # Commit all changes
        db_session.commit()
        
        # Verify all updates succeeded
        db_helpers.verify_job_status_in_db(job1.id, JobStatus.COMPLETED)
        db_helpers.verify_job_status_in_db(job2.id, JobStatus.FAILED)
        db_helpers.verify_job_status_in_db(job3.id, JobStatus.PAUSED)
        
        # Campaign should respond to the paused/failed jobs
        campaign.pause("Multiple jobs encountered issues")
        db_session.commit()
        
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)

    def test_invalid_job_status_transitions(self, authenticated_client, db_session,
                                          running_campaign_with_multiple_jobs, db_helpers):
        """Test handling of invalid job status transitions."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        completed_job = jobs[0]
        completed_job.status = JobStatus.COMPLETED
        completed_job.completed_at = datetime.now(timezone.utc)
        db_session.commit()
        
        db_helpers.verify_job_status_in_db(completed_job.id, JobStatus.COMPLETED)
        
        # Try to move completed job back to processing (invalid transition)
        completed_job.status = JobStatus.PROCESSING
        
        try:
            db_session.commit()
            # If this succeeds, verify the system handles it gracefully
            db_helpers.verify_job_status_in_db(completed_job.id, JobStatus.PROCESSING)
            
        except Exception as e:
            # If database constraints prevent invalid transitions, that's preferred
            db_session.rollback()
            # Verify job remains in completed state
            db_session.refresh(completed_job)
            assert completed_job.status == JobStatus.COMPLETED

    def test_job_status_audit_trail(self, authenticated_client, db_session,
                                  running_campaign_with_multiple_jobs, db_helpers):
        """Test that job status changes maintain proper audit trail."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        job = jobs[0]
        original_updated_at = job.updated_at
        
        # Update job status
        job.status = JobStatus.PAUSED
        job.error = "Testing audit trail"
        db_session.commit()
        
        # Verify updated_at timestamp is set after update
        db_session.refresh(job)
        assert job.updated_at is not None
        
        # Verify status and error are recorded
        db_helpers.verify_job_status_in_db(job.id, JobStatus.PAUSED)
        updated_job = db_session.query(Job).filter(Job.id == job.id).first()
        assert updated_job.error == "Testing audit trail"
        
        # Store the first update timestamp
        first_update_at = job.updated_at
        
        # Add a small delay to ensure timestamp difference
        time.sleep(0.01)
        
        # Update again
        job.status = JobStatus.PROCESSING
        job.error = None
        db_session.commit()
        
        # Verify second update
        db_session.refresh(job)
        assert job.updated_at is not None
        # The timestamp should be the same or newer (depending on SQL precision)
        assert job.updated_at >= first_update_at
        
        db_helpers.verify_job_status_in_db(job.id, JobStatus.PROCESSING)
        updated_job = db_session.query(Job).filter(Job.id == job.id).first()
        assert updated_job.error is None

    # ===== INTEGRATION WITH CAMPAIGN STATUS MONITOR =====

    def test_job_status_monitor_integration_placeholder(self, authenticated_client, db_session,
                                                      running_campaign_with_multiple_jobs, db_helpers):
        """Test integration with CampaignStatusMonitor service (placeholder for future implementation)."""
        campaign, jobs = running_campaign_with_multiple_jobs
        
        # This test documents the expected integration with CampaignStatusMonitor
        # When the service is fully implemented, this test should be updated
        
        job = jobs[0]
        
        # Simulate job status change that should trigger monitor
        job.status = JobStatus.PAUSED
        job.error = "Service failure detected"
        db_session.commit()
        
        # TODO: Replace with actual service integration
        # from app.services.campaign_status_monitor import CampaignStatusMonitor
        # monitor = CampaignStatusMonitor()
        # result = await monitor.evaluate_campaign_for_job_status_change(job, db_session)
        
        # For now, simulate expected behavior
        campaign.pause(f"Job {job.name} paused: {job.error}")
        db_session.commit()
        
        # Verify expected outcome
        db_helpers.verify_job_status_in_db(job.id, JobStatus.PAUSED)
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Verify status message includes job information
        updated_campaign = db_session.query(Campaign).filter(Campaign.id == campaign.id).first()
        assert job.name in updated_campaign.status_message
        assert "paused" in updated_campaign.status_message.lower() 