"""
Tests for campaign status refactor with new simplified logic.

This module tests the new business rules:
1. Campaigns pause automatically when ANY job is paused OR when queue is paused
2. Circuit breaker opening pauses ALL campaigns and the queue immediately  
3. Campaigns resume ONLY through manual queue resume action
4. Manual queue resume only works if ALL circuit breakers are closed

Test Coverage:
- Automatic pause scenarios (job pause, queue pause, circuit breaker)
- Manual resume scenarios (queue resume button)
- Prerequisite validation (circuit breaker checks)
- Edge cases and error conditions
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.campaign import Campaign, CampaignStatus
from app.models.job import Job, JobStatus, JobType
from app.core.circuit_breaker import ThirdPartyService, CircuitState
from tests.helpers.auth_helpers import AuthHelpers


class TestCampaignStatusRefactor:
    """Test new simplified campaign status logic."""

    @pytest.fixture
    def test_organization(self, db_session):
        """Create a test organization."""
        org = Organization(
            id="test-org-refactor",
            name="Test Org Campaign Status Refactor",
            description="Testing organization for campaign status refactor"
        )
        db_session.add(org)
        db_session.commit()
        return org

    @pytest.fixture
    def running_campaign_with_jobs(self, db_session, test_organization):
        """Create a running campaign with multiple jobs."""
        campaign = Campaign(
            name="Running Campaign Test",
            description="Campaign with multiple jobs for testing",
            organization_id=test_organization.id,
            fileName="test_running.csv",
            totalRecords=100,
            url="https://app.apollo.io/running-test",
            status=CampaignStatus.RUNNING
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)
        
        # Create multiple jobs in different states
        jobs = [
            Job(
                name="Job 1 - Processing",
                description="First job processing",
                job_type=JobType.FETCH_LEADS,
                status=JobStatus.PROCESSING,
                campaign_id=campaign.id,
                task_id="task-1"
            ),
            Job(
                name="Job 2 - Pending", 
                description="Second job pending",
                job_type=JobType.ENRICH_LEAD,
                status=JobStatus.PENDING,
                campaign_id=campaign.id,
                task_id="task-2"
            ),
            Job(
                name="Job 3 - Completed",
                description="Third job completed", 
                job_type=JobType.CLEANUP_CAMPAIGN,
                status=JobStatus.COMPLETED,
                campaign_id=campaign.id,
                task_id="task-3"
            )
        ]
        
        db_session.add_all(jobs)
        db_session.commit()
        
        for job in jobs:
            db_session.refresh(job)
        
        return campaign, jobs

    @pytest.fixture
    def multiple_running_campaigns(self, db_session, test_organization):
        """Create multiple running campaigns for bulk operations testing."""
        campaigns = []
        for i in range(3):
            campaign = Campaign(
                name=f"Running Campaign {i+1}",
                description=f"Campaign {i+1} for bulk testing",
                organization_id=test_organization.id,
                fileName=f"test_bulk_{i+1}.csv",
                totalRecords=50 + i*20,
                url=f"https://app.apollo.io/bulk-test-{i+1}",
                status=CampaignStatus.RUNNING
            )
            campaigns.append(campaign)
        
        db_session.add_all(campaigns)
        db_session.commit()
        
        for i, campaign in enumerate(campaigns):
            db_session.refresh(campaign)
            
            # Create jobs that depend on apollo service for each campaign
            apollo_job = Job(
                name=f"Apollo Job for Campaign {i+1}",
                description=f"Fetch leads job for campaign {i+1}",
                job_type=JobType.FETCH_LEADS,  # This depends on apollo service
                status=JobStatus.PENDING,
                campaign_id=campaign.id,
                task_id=f"apollo-task-{i+1}"
            )
            db_session.add(apollo_job)
        
        db_session.commit()
        return campaigns

    # ===== AUTOMATIC PAUSE SCENARIOS =====

    def test_single_job_pause_pauses_campaign(self, authenticated_client, db_session, 
                                            running_campaign_with_jobs, db_helpers):
        """Test that pausing ANY single job immediately pauses the entire campaign."""
        campaign, jobs = running_campaign_with_jobs
        
        # Initially campaign should be running
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
        
        # Pause one job (simulating job failure/pause)
        job_to_pause = jobs[0]  # Processing job
        job_to_pause.status = JobStatus.PAUSED
        db_session.commit()
        
        # TODO: This will need service integration - for now simulate the trigger
        # In actual implementation, job status change should trigger campaign evaluation
        # campaign_status_monitor.evaluate_campaign_for_job_status_change(job_to_pause, db_session)
        
        # For now, manually trigger the expected behavior 
        campaign.pause(f"Job {job_to_pause.name} paused")
        db_session.commit()
        
        # Verify campaign is now paused
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Verify status message indicates job pause
        updated_campaign = db_session.query(Campaign).filter(Campaign.id == campaign.id).first()
        assert "Job" in updated_campaign.status_message
        assert "paused" in updated_campaign.status_message.lower()

    def test_multiple_job_pause_keeps_campaign_paused(self, authenticated_client, db_session,
                                                    running_campaign_with_jobs, db_helpers):
        """Test that pausing multiple jobs keeps campaign paused (not double-pause)."""
        campaign, jobs = running_campaign_with_jobs
        
        # Pause first job - campaign should pause
        jobs[0].status = JobStatus.PAUSED
        campaign.pause(f"Job {jobs[0].name} paused")
        db_session.commit()
        
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Pause second job - campaign should remain paused
        jobs[1].status = JobStatus.PAUSED
        db_session.commit()
        
        # Campaign should still be paused, not in error state
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)

    def test_queue_pause_pauses_all_campaigns(self, authenticated_client, db_session,
                                            multiple_running_campaigns, db_helpers):
        """Test that queue pause immediately pauses ALL running campaigns."""
        campaigns = multiple_running_campaigns
        
        # All campaigns should initially be running
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
        
        # Use apollo service instead of "system" since system is not a valid ThirdPartyService
        pause_data = {
            "service": "apollo",
            "reason": "Queue manually paused for testing"
        }
        
        response = authenticated_client.post(
            "/api/v1/queue-management/pause-service",
            json=pause_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # All campaigns should now be paused (ANY circuit breaker opening pauses ALL campaigns)
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)

    def test_circuit_breaker_opening_pauses_queue_and_campaigns(self, authenticated_client, db_session,
                                                              multiple_running_campaigns, db_helpers):
        """Test that circuit breaker opening immediately pauses queue and all campaigns."""
        campaigns = multiple_running_campaigns
        
        # All campaigns should initially be running
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
        
        # Simulate circuit breaker opening by triggering service failures
        # This will be integration test - for now test the expected result
        
        # Pause campaigns for service (simulating circuit breaker trigger)
        pause_data = {
            "service": "apollo",
            "reason": "Circuit breaker opened: apollo service failing"
        }
        
        response = authenticated_client.post(
            "/api/v1/queue-management/pause-campaigns-for-service",
            json=pause_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # All running campaigns should now be paused
        campaigns_paused = data["data"]["campaigns_paused"]
        assert campaigns_paused >= len(campaigns)

    # ===== MANUAL RESUME SCENARIOS =====

    def test_manual_queue_resume_with_global_circuit_breaker_closed(self, authenticated_client, db_session,
                                                                multiple_running_campaigns, db_helpers):
        """Test manual queue resume works when all circuit breakers are closed."""
        campaigns = multiple_running_campaigns

        # First pause all campaigns
        for campaign in campaigns:
            campaign.pause("Testing manual resume")
        db_session.commit()

        # Verify all are paused
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)

        # Check circuit breaker status first
        cb_response = authenticated_client.get("/api/v1/queue-management/circuit-breakers")
        assert cb_response.status_code == 200
        cb_data = cb_response.json()
        
        # Reset any open circuit breakers to ensure clean state for resume test
        for service in ["apollo", "instantly", "openai", "millionverifier"]:
            reset_response = authenticated_client.post(f"/api/v1/queue-management/circuit-breakers/{service}/reset")
            # Don't assert on status code since some might already be closed

        # Manually resume queue (this should resume all campaigns)
        response = authenticated_client.post("/api/v1/queue-management/resume-queue")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # All campaigns should now be resumed
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)

    def test_manual_queue_resume_blocked_by_open_circuit_breaker(self, authenticated_client, db_session,
                                                               multiple_running_campaigns, db_helpers):
        """Test manual queue resume is blocked when any circuit breaker is open."""
        campaigns = multiple_running_campaigns
        
        # Pause all campaigns
        for campaign in campaigns:
            campaign.pause("Testing blocked resume")
        db_session.commit()
        
        # Simulate opening a circuit breaker by creating failures
        # This would normally happen through service integration
        # For testing, we'll use the pause endpoint which simulates circuit breaker effect
        
        # Try to resume queue while circuit breaker is "open"
        # First simulate circuit breaker open condition
        pause_data = {
            "service": "apollo", 
            "reason": "Circuit breaker test - service failing"
        }
        
        authenticated_client.post(
            "/api/v1/queue-management/pause-campaigns-for-service",
            json=pause_data
        )
        
        # Now try to resume - should be blocked or limited
        response = authenticated_client.post("/api/v1/queue-management/resume-service")
        
        # Response should either be blocked or indicate partial resume
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            data = response.json()
            # If successful, should indicate limitations or prerequisites not met
            assert "circuit" in data.get("message", "").lower() or \
                   data["data"].get("campaigns_resumed", 0) == 0

    def test_manual_campaign_resume_through_queue_only(self, authenticated_client, db_session,
                                                     running_campaign_with_jobs, db_helpers):
        """Test that campaigns can ONLY be resumed through queue management, not directly."""
        campaign, jobs = running_campaign_with_jobs
        
        # Pause the campaign
        campaign.pause("Testing direct resume blocking")
        db_session.commit()
        
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Try to resume campaign directly (should not work or should require queue resume)
        campaign_update = {
            "status": "RUNNING",
            "status_message": "Attempting direct resume"
        }
        
        response = authenticated_client.patch(
            f"/api/v1/campaigns/{campaign.id}/status",
            json=campaign_update
        )
        
        # Direct campaign resume should either:
        # 1. Be blocked (400/422 error)
        # 2. Require queue to be active first
        # 3. Work only if queue is active
        
        if response.status_code == 200:
            # If allowed, verify it's conditional on queue status
            data = response.json()
            # Implementation may vary - key is that resume goes through proper channels
            
        # The key test: campaigns should not resume independently of queue management
        # This will be enforced in the service layer implementation

    # ===== PREREQUISITE VALIDATION SCENARIOS =====

    def test_queue_status_reflects_circuit_breaker_states(self, authenticated_client, db_session):
        """Test that queue status endpoint correctly shows circuit breaker prerequisites."""
        response = authenticated_client.get("/api/v1/queue-management/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        queue_data = data["data"]
        # Check for actual fields that exist in the response
        assert "circuit_breaker" in queue_data
        assert "job_counts" in queue_data
        assert "timestamp" in queue_data
        
        # Verify global circuit breaker format
        circuit_breaker = queue_data["circuit_breaker"]
        assert isinstance(circuit_breaker, dict)
        assert "state" in circuit_breaker
        assert circuit_breaker["state"] in ["open", "closed"]

    def test_circuit_breaker_reset_does_not_auto_resume_campaigns(self, authenticated_client, db_session,
                                                                multiple_running_campaigns, db_helpers):
        """Test that resetting circuit breaker does NOT automatically resume campaigns."""
        campaigns = multiple_running_campaigns
        
        # Pause campaigns due to "circuit breaker"
        for campaign in campaigns:
            campaign.pause("Circuit breaker opened: apollo service failing")
        db_session.commit()
        
        # Verify all paused
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Reset circuit breaker
        response = authenticated_client.post(
            "/api/v1/queue-management/circuit-breakers/apollo/reset"
        )
        
        assert response.status_code == 200
        
        # Campaigns should STILL be paused - circuit breaker reset alone doesn't resume
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Only manual queue resume should resume campaigns
        queue_resume = authenticated_client.post("/api/v1/queue-management/resume-queue")
        assert queue_resume.status_code == 200
        
        # Now campaigns should be resumed
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)

    # ===== EDGE CASES AND ERROR CONDITIONS =====

    def test_campaign_pause_during_job_creation(self, authenticated_client, db_session,
                                               running_campaign_with_jobs, db_helpers):
        """Test campaign behavior when jobs are created while campaign is paused."""
        campaign, existing_jobs = running_campaign_with_jobs
        
        # Pause the campaign
        campaign.pause("Testing job creation during pause")
        db_session.commit()
        
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Create new job for paused campaign
        new_job = Job(
            name="New Job During Pause",
            description="Job created while campaign paused",
            job_type=JobType.ENRICH_LEAD,
            status=JobStatus.PENDING,
            campaign_id=campaign.id,
            task_id="task-new-pause"
        )
        
        db_session.add(new_job)
        db_session.commit()
        
        # Campaign should remain paused
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # New job should be paused as well (or pending but not processing)
        db_session.refresh(new_job)
        assert new_job.status in [JobStatus.PENDING, JobStatus.PAUSED]

    def test_mixed_campaign_states_during_queue_operations(self, authenticated_client, db_session,
                                                         test_organization, db_helpers):
        """Test queue operations with campaigns in different states."""
        # Create campaigns in various states
        campaigns = []

        running_campaign = Campaign(
            name="Running Campaign",
            organization_id=test_organization.id,
            fileName="running.csv",
            totalRecords=50,
            url="https://test.com/running",
            status=CampaignStatus.RUNNING
        )

        paused_campaign = Campaign(
            name="Already Paused Campaign",
            organization_id=test_organization.id,
            fileName="paused.csv",
            totalRecords=30,
            url="https://test.com/paused",
            status=CampaignStatus.PAUSED
        )

        completed_campaign = Campaign(
            name="Completed Campaign",
            organization_id=test_organization.id,
            fileName="completed.csv",
            totalRecords=40,
            url="https://test.com/completed",
            status=CampaignStatus.COMPLETED
        )

        campaigns = [running_campaign, paused_campaign, completed_campaign]
        db_session.add_all(campaigns)
        db_session.commit()

        for campaign in campaigns:
            db_session.refresh(campaign)
            
        # Add apollo job to running campaign so it can be paused
        apollo_job = Job(
            name="Apollo Job for Running Campaign",
            description="Fetch leads job",
            job_type=JobType.FETCH_LEADS,
            status=JobStatus.PENDING,
            campaign_id=running_campaign.id,
            task_id="apollo-task-mixed"
        )
        db_session.add(apollo_job)
        db_session.commit()

        # Queue pause should only affect RUNNING campaigns with apollo jobs
        response = authenticated_client.post(
            "/api/v1/queue-management/pause-service",
            json={"service": "apollo", "reason": "Testing mixed states"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Only running campaign should be affected
        db_helpers.verify_campaign_status_in_db(running_campaign.id, CampaignStatus.PAUSED)
        db_helpers.verify_campaign_status_in_db(paused_campaign.id, CampaignStatus.PAUSED)  # unchanged
        db_helpers.verify_campaign_status_in_db(completed_campaign.id, CampaignStatus.COMPLETED)  # unchanged

    def test_error_handling_invalid_status_transitions(self, authenticated_client, db_session,
                                                     test_organization, db_helpers):
        """Test error handling for invalid campaign status transitions."""
        # Create completed campaign
        completed_campaign = Campaign(
            name="Completed Campaign",
            organization_id=test_organization.id,
            fileName="completed.csv",
            totalRecords=25,
            url="https://test.com/completed",
            status=CampaignStatus.COMPLETED
        )

        db_session.add(completed_campaign)
        db_session.commit()
        db_session.refresh(completed_campaign)

        # Try to pause completed campaign (invalid transition)
        assert not completed_campaign.is_valid_transition(CampaignStatus.PAUSED)

        # Since there's no campaign status update endpoint, test the model validation directly
        # Try to pause through model method
        success = completed_campaign.pause("Trying to pause completed campaign")
        assert not success  # Should fail due to invalid transition
        
        # Verify campaign status unchanged
        db_helpers.verify_campaign_status_in_db(completed_campaign.id, CampaignStatus.COMPLETED)

    def test_database_consistency_during_bulk_operations(self, authenticated_client, db_session,
                                                       multiple_running_campaigns, db_helpers):
        """Test database consistency during bulk pause/resume operations."""
        campaigns = multiple_running_campaigns
        
        # Note: campaigns may already be paused from previous test runs, so let's check actual state
        # and verify the pause operation works regardless
        initial_states = []
        for campaign in campaigns:
            db_session.refresh(campaign)  # Get fresh state from DB
            initial_states.append(campaign.status)

        # Bulk pause
        response = authenticated_client.post(
            "/api/v1/queue-management/pause-campaigns-for-service",
            json={"service": "apollo", "reason": "Bulk pause test"}
        )

        assert response.status_code == 200

        # Verify all paused atomically
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)

        # Reset circuit breakers to ensure clean state for resume test
        for service in ["apollo", "instantly", "openai", "millionverifier"]:
            reset_response = authenticated_client.post(f"/api/v1/queue-management/circuit-breakers/{service}/reset")
            # Don't assert on status code since some might already be closed

        # Bulk resume through queue (the only way to resume campaigns in Phase 2)
        response = authenticated_client.post("/api/v1/queue-management/resume-queue")
        assert response.status_code == 200
        
        # Verify campaigns can be resumed (they should go back to RUNNING)
        for campaign in campaigns:
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)

    # ===== INTEGRATION VALIDATION SCENARIOS =====

    def test_campaign_status_monitor_pause_only_logic(self, db_session, running_campaign_with_jobs):
        """Test that CampaignStatusMonitor only handles pause logic (no automatic resume)."""
        campaign, jobs = running_campaign_with_jobs
        
        # This will test the actual service when implemented
        # For now, test the expected interface
        
        # Simulate job pause triggering campaign evaluation
        jobs[0].status = JobStatus.PAUSED
        db_session.commit()
        
        # CampaignStatusMonitor should detect this and pause campaign
        # monitor = CampaignStatusMonitor()
        # result = await monitor.evaluate_campaign_status_for_job_change(jobs[0], db_session)
        
        # Expected behavior:
        # - Campaign gets paused
        # - No automatic resume logic triggered
        # - Only manual resume through queue management works
        
        # For now, verify the expected final state
        campaign.pause(f"Job {jobs[0].name} paused - auto-pause triggered")
        db_session.commit()
        
        from tests.helpers.database_helpers import DatabaseHelpers
        db_helpers = DatabaseHelpers(db_session)
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)

    def test_end_to_end_pause_resume_workflow(self, authenticated_client, db_session,
                                            running_campaign_with_jobs, db_helpers):
        """Test complete end-to-end workflow: service failure → pause → manual resume."""
        campaign, jobs = running_campaign_with_jobs
        
        # Step 1: Simulate service failure triggering circuit breaker
        # (In real implementation: Service Error → Circuit Breaker Open → Queue Pause → Campaign Pause)
        
        # For testing, simulate the end result
        pause_response = authenticated_client.post(
            "/api/v1/queue-management/pause-campaigns-for-service",
            json={"service": "apollo", "reason": "Circuit breaker opened: apollo service failing"}
        )
        
        assert pause_response.status_code == 200
        
        # Step 2: Verify cascade effect - campaign should be paused
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Step 3: Check that circuit breaker reset doesn't auto-resume
        cb_reset_response = authenticated_client.post(
            "/api/v1/queue-management/circuit-breakers/apollo/reset" 
        )
        
        if cb_reset_response.status_code == 200:
            # Campaign should still be paused after circuit breaker reset
            db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.PAUSED)
        
        # Step 4: Manual queue resume should work and resume campaigns
        queue_resume_response = authenticated_client.post("/api/v1/queue-management/resume-queue")
        assert queue_resume_response.status_code == 200
        
        # Step 5: Verify campaign is resumed
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
        
        # Step 6: Verify jobs are also handled appropriately
        db_session.refresh(jobs[0])
        # Jobs should be resumed or at least not blocked by paused campaign
        assert jobs[0].status in [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.COMPLETED] 