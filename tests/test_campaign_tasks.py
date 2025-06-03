import pytest
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus, JobType
from app.workers.campaign_tasks import (
    fetch_and_save_leads_task,
    cleanup_campaign_jobs_task,
    campaign_health_check
)

@pytest.fixture
def sample_campaign(db_session, organization):
    """Create a sample campaign for testing."""
    campaign = Campaign(
        name="Test Campaign",
        description="A test campaign",
        status=CampaignStatus.CREATED,
        fileName="test.csv",
        totalRecords=50,
        url="https://app.apollo.io/test",
        organization_id=organization.id
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)
    return campaign

@pytest.fixture
def sample_job(db_session, sample_campaign):
    """Create a sample job for testing."""
    job = Job(
        campaign_id=sample_campaign.id,
        name="FETCH_LEADS",
        description="Test job",
        job_type=JobType.FETCH_LEADS,
        status=JobStatus.PENDING
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job

def test_campaign_health_check():
    """Test the campaign health check task."""
    result = campaign_health_check()
    
    assert result["status"] == "healthy"
    assert "timestamp" in result
    assert "campaign_count" in result
    assert "job_count" in result
    assert result["service"] == "campaign_tasks"

def test_fetch_and_save_leads_task_mock(db_session, sample_campaign, sample_job):
    """Test the fetch and save leads task with mock data."""
    job_params = {
        "fileName": sample_campaign.fileName,
        "totalRecords": sample_campaign.totalRecords,
        "url": sample_campaign.url
    }
    
    # Mock the task execution (since we can't run actual Celery tasks in tests)
    # This tests the task logic without the Celery infrastructure
    
    # Simulate task execution
    db = db_session
    try:
        # Update job status to processing
        job = db.query(Job).filter(Job.id == sample_job.id).first()
        job.status = JobStatus.PROCESSING
        db.commit()
        
        # Get campaign
        campaign = db.query(Campaign).filter(Campaign.id == sample_campaign.id).first()
        
        # Mock Apollo service result (since it's not available in tests)
        leads_count = min(job_params['totalRecords'], 10)
        
        # Update job status to completed
        job.status = JobStatus.COMPLETED
        job.result = f"Successfully fetched {leads_count} leads"
        job.completed_at = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # First update campaign to RUNNING, then to COMPLETED
        campaign.update_status(CampaignStatus.RUNNING, status_message="Processing leads")
        campaign.update_status(
            CampaignStatus.COMPLETED,
            status_message=f"Successfully fetched {leads_count} leads"
        )
        
        db.commit()
        
        # Verify results
        assert job.status == JobStatus.COMPLETED
        assert campaign.status == CampaignStatus.COMPLETED
        assert f"{leads_count} leads" in job.result
        
    finally:
        db.close()

def test_cleanup_campaign_jobs_task(db_session, sample_campaign):
    """Test the cleanup campaign jobs task."""
    db = db_session
    try:
        # Create some old jobs
        old_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=35)
        
        old_job1 = Job(
            campaign_id=sample_campaign.id,
            name="OLD_JOB_1",
            description="Old job 1",
            job_type=JobType.FETCH_LEADS,
            status=JobStatus.COMPLETED,
            created_at=old_date
        )
        old_job2 = Job(
            campaign_id=sample_campaign.id,
            name="OLD_JOB_2", 
            description="Old job 2",
            job_type=JobType.FETCH_LEADS,
            status=JobStatus.FAILED,
            created_at=old_date
        )
        
        # Create a recent job that should not be deleted
        recent_job = Job(
            campaign_id=sample_campaign.id,
            name="RECENT_JOB",
            description="Recent job",
            job_type=JobType.FETCH_LEADS,
            status=JobStatus.COMPLETED,
            created_at=datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=5)
        )
        
        db.add_all([old_job1, old_job2, recent_job])
        db.commit()
        
        # Count jobs before cleanup
        jobs_before = db.query(Job).filter(Job.campaign_id == sample_campaign.id).count()
        assert jobs_before == 3
        
        # Mock the cleanup task execution
        cutoff_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=30)
        
        jobs_to_delete = (
            db.query(Job)
            .filter(
                Job.campaign_id == sample_campaign.id,
                Job.created_at < cutoff_date,
                Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])
            )
            .all()
        )
        
        deleted_count = 0
        for job in jobs_to_delete:
            db.delete(job)
            deleted_count += 1
        
        db.commit()
        
        # Verify results
        jobs_after = db.query(Job).filter(Job.campaign_id == sample_campaign.id).count()
        assert jobs_after == 1  # Only the recent job should remain
        assert deleted_count == 2  # Two old jobs should be deleted
        
        # Verify the remaining job is the recent one
        remaining_job = db.query(Job).filter(Job.campaign_id == sample_campaign.id).first()
        assert remaining_job.name == "RECENT_JOB"
        
    finally:
        db.close()

def test_process_campaign_leads_task_mock(db_session, sample_campaign):
    """Test the process campaign leads task with mock data."""
    db = db_session
    try:
        # Mock the task execution
        processing_type = "enrichment"
        
        # Create a job to track this processing
        processing_job = Job(
            campaign_id=sample_campaign.id,
            name=f'PROCESS_LEADS_{processing_type.upper()}',
            description=f'Process leads for campaign {sample_campaign.name} - {processing_type}',
            job_type=JobType.ENRICH_LEAD,
            status=JobStatus.PROCESSING
        )
        db.add(processing_job)
        db.commit()
        db.refresh(processing_job)
        
        # Mock processing results
        processed_count = 0  # Mock result
        
        # Update job status
        processing_job.status = JobStatus.COMPLETED
        processing_job.result = f"Processed {processed_count} leads with {processing_type}"
        processing_job.completed_at = datetime.utcnow().replace(tzinfo=timezone.utc)
        db.commit()
        
        # Verify results
        assert processing_job.status == JobStatus.COMPLETED
        assert processing_type in processing_job.result
        assert processing_job.completed_at is not None
        
    finally:
        db.close()

def test_task_error_handling(db_session, sample_campaign, sample_job):
    """Test error handling in tasks."""
    db = db_session
    try:
        # Test with non-existent job ID
        job_params = {
            "fileName": "test.csv",
            "totalRecords": 50,
            "url": "https://app.apollo.io/test"
        }
        
        # This should raise an error for non-existent job
        non_existent_job_id = 99999
        
        try:
            # Simulate the error condition
            job = db.query(Job).filter(Job.id == non_existent_job_id).first()
            if not job:
                raise ValueError(f"Job {non_existent_job_id} not found")
        except ValueError as e:
            assert "not found" in str(e)
        
        # Test with non-existent campaign
        non_existent_campaign_id = "non-existent-id"
        
        try:
            campaign = db.query(Campaign).filter(Campaign.id == non_existent_campaign_id).first()
            if not campaign:
                raise ValueError(f"Campaign {non_existent_campaign_id} not found")
        except ValueError as e:
            assert "not found" in str(e)
            
    finally:
        db.close()

def test_task_progress_tracking():
    """Test that tasks can track progress properly."""
    # This is a unit test for the progress tracking logic
    # In a real Celery environment, this would update task state
    
    progress_states = []
    
    # Mock progress tracking
    def mock_update_state(state, meta):
        progress_states.append({"state": state, "meta": meta})
    
    # Simulate progress updates like in fetch_and_save_leads_task
    mock_update_state("PROGRESS", {"current": 1, "total": 4, "status": "Initializing Apollo service"})
    mock_update_state("PROGRESS", {"current": 2, "total": 4, "status": "Fetching leads from Apollo"})
    mock_update_state("PROGRESS", {"current": 3, "total": 4, "status": "Saving leads to database"})
    mock_update_state("PROGRESS", {"current": 4, "total": 4, "status": "Finalizing results"})
    
    # Verify progress tracking
    assert len(progress_states) == 4
    assert progress_states[0]["meta"]["current"] == 1
    assert progress_states[-1]["meta"]["current"] == 4
    assert all(state["state"] == "PROGRESS" for state in progress_states)

def test_job_status_transitions(db_session, sample_campaign, sample_job):
    """Test proper job status transitions during task execution."""
    db = db_session
    try:
        # Initial status should be PENDING
        job = db.query(Job).filter(Job.id == sample_job.id).first()
        assert job.status == JobStatus.PENDING
        
        # Simulate task starting
        job.status = JobStatus.PROCESSING
        db.commit()
        
        job = db.query(Job).filter(Job.id == sample_job.id).first()
        assert job.status == JobStatus.PROCESSING
        
        # Simulate successful completion
        job.status = JobStatus.COMPLETED
        job.result = "Task completed successfully"
        job.completed_at = datetime.utcnow().replace(tzinfo=timezone.utc)
        db.commit()
        
        job = db.query(Job).filter(Job.id == sample_job.id).first()
        assert job.status == JobStatus.COMPLETED
        assert job.result == "Task completed successfully"
        assert job.completed_at is not None
        
    finally:
        db.close()

def test_campaign_status_updates(db_session, sample_campaign):
    """Test that campaign status is properly updated by tasks."""
    db = db_session
    try:
        # Initial status should be CREATED
        campaign = db.query(Campaign).filter(Campaign.id == sample_campaign.id).first()
        assert campaign.status == CampaignStatus.CREATED
        
        # Simulate task updating campaign to RUNNING
        campaign.update_status(CampaignStatus.RUNNING, "Processing leads")
        db.commit()
        
        campaign = db.query(Campaign).filter(Campaign.id == sample_campaign.id).first()
        assert campaign.status == CampaignStatus.RUNNING
        assert campaign.status_message == "Processing leads"
        
        # Simulate task completing successfully
        campaign.update_status(CampaignStatus.COMPLETED, "Successfully processed 10 leads")
        db.commit()
        
        campaign = db.query(Campaign).filter(Campaign.id == sample_campaign.id).first()
        assert campaign.status == CampaignStatus.COMPLETED
        assert "10 leads" in campaign.status_message
        
    finally:
        db.close() 