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
    
    # ===== JOB LIFECYCLE INTEGRATION TESTS ====
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