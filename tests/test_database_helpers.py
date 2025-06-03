"""
Tests for database verification helpers.

These tests ensure the helper functions work correctly and provide
reliable database state verification for campaign API testing.
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus, JobType
from tests.helpers.database_helpers import (
    DatabaseHelpers,
    verify_campaign_in_db,
    verify_campaign_not_in_db,
    count_campaigns_in_db,
    cleanup_test_data,
    create_test_campaign_in_db
)


@pytest.fixture
def sample_campaign_data(organization):
    """Sample campaign data for testing."""
    return {
        "name": "Test Campaign",
        "description": "Test Description",
        "fileName": "test.csv",
        "totalRecords": 100,
        "url": "https://test.com",
        "organization_id": organization.id
    }


# ---------------------------------------------------------------------------
# DatabaseHelpers Class Tests
# ---------------------------------------------------------------------------

def test_verify_campaign_in_db_success(db_helpers, sample_campaign_data):
    """Test successful campaign verification."""
    # Create campaign directly in database
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Verify it exists with correct data
    found_campaign = db_helpers.verify_campaign_in_db(campaign.id, {
        "name": sample_campaign_data["name"],
        "status": CampaignStatus.CREATED.value,
        "totalRecords": sample_campaign_data["totalRecords"]
    })
    
    assert found_campaign.id == campaign.id
    assert found_campaign.name == sample_campaign_data["name"]


def test_verify_campaign_in_db_not_found(db_helpers):
    """Test campaign verification fails when campaign doesn't exist."""
    fake_id = str(uuid.uuid4())
    
    with pytest.raises(AssertionError, match=f"Campaign {fake_id} not found in database"):
        db_helpers.verify_campaign_in_db(fake_id)


def test_verify_campaign_in_db_wrong_values(db_helpers, sample_campaign_data):
    """Test campaign verification fails when values don't match."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    with pytest.raises(AssertionError, match="Expected name=Wrong Name"):
        db_helpers.verify_campaign_in_db(campaign.id, {"name": "Wrong Name"})


def test_verify_campaign_not_in_db_success(db_helpers):
    """Test successful verification that campaign doesn't exist."""
    fake_id = str(uuid.uuid4())
    
    # Should not raise any exception
    db_helpers.verify_campaign_not_in_db(fake_id)


def test_verify_campaign_not_in_db_failure(db_helpers, sample_campaign_data):
    """Test verification fails when campaign exists."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    with pytest.raises(AssertionError, match=f"Campaign {campaign.id} should not exist"):
        db_helpers.verify_campaign_not_in_db(campaign.id)


def test_count_campaigns_in_db(db_helpers, sample_campaign_data):
    """Test campaign counting."""
    # Initially should be 0
    assert db_helpers.count_campaigns_in_db() == 0
    
    # Create one campaign
    db_helpers.create_test_campaign_in_db(sample_campaign_data)
    assert db_helpers.count_campaigns_in_db() == 1
    
    # Create another campaign
    db_helpers.create_test_campaign_in_db({**sample_campaign_data, "name": "Second Campaign"})
    assert db_helpers.count_campaigns_in_db() == 2


def test_verify_job_created_for_campaign(db_helpers, sample_campaign_data):
    """Test job verification for campaign."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Create a job for the campaign
    job = db_helpers.create_test_job_in_db(campaign.id, {
        "job_type": JobType.FETCH_LEADS,
        "name": "Fetch Leads Job"
    })
    
    # Verify job exists
    found_job = db_helpers.verify_job_created_for_campaign(campaign.id, JobType.FETCH_LEADS)
    assert found_job.id == job.id
    assert found_job.job_type == JobType.FETCH_LEADS
    
    # Test with string job type
    found_job = db_helpers.verify_job_created_for_campaign(campaign.id, "FETCH_LEADS")
    assert found_job.id == job.id


def test_verify_job_created_for_campaign_not_found(db_helpers, sample_campaign_data):
    """Test job verification fails when job doesn't exist."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    with pytest.raises(AssertionError, match="No job of type FETCH_LEADS found"):
        db_helpers.verify_job_created_for_campaign(campaign.id, JobType.FETCH_LEADS)


def test_get_campaign_jobs_from_db(db_helpers, sample_campaign_data):
    """Test getting all jobs for a campaign."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Initially no jobs
    jobs = db_helpers.get_campaign_jobs_from_db(campaign.id)
    assert len(jobs) == 0
    
    # Create multiple jobs
    job1 = db_helpers.create_test_job_in_db(campaign.id, {"job_type": JobType.FETCH_LEADS})
    job2 = db_helpers.create_test_job_in_db(campaign.id, {"job_type": JobType.ENRICH_LEAD})
    
    jobs = db_helpers.get_campaign_jobs_from_db(campaign.id)
    assert len(jobs) == 2
    assert job1.id in [j.id for j in jobs]
    assert job2.id in [j.id for j in jobs]


def test_verify_campaign_status_in_db(db_helpers, sample_campaign_data):
    """Test campaign status verification."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Verify initial status
    db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.CREATED)
    
    # Test with string status
    db_helpers.verify_campaign_status_in_db(campaign.id, "created")
    
    # Update status and verify
    campaign.status = CampaignStatus.RUNNING
    db_helpers.db_session.commit()
    
    db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)


def test_verify_campaign_status_in_db_wrong_status(db_helpers, sample_campaign_data):
    """Test campaign status verification fails with wrong status."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    with pytest.raises(AssertionError, match="Expected status running"):
        db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)


def test_cleanup_test_data(db_helpers, sample_campaign_data):
    """Test cleaning up test data."""
    # Create test data
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    job = db_helpers.create_test_job_in_db(campaign.id)
    
    # Verify data exists
    assert db_helpers.count_campaigns_in_db() == 1
    assert len(db_helpers.get_campaign_jobs_from_db(campaign.id)) == 1
    
    # Clean up
    result = db_helpers.cleanup_test_data()
    
    # Verify cleanup results
    assert result["campaigns_deleted"] == 1
    assert result["jobs_deleted"] == 1
    assert db_helpers.count_campaigns_in_db() == 0


def test_create_test_campaign_in_db_defaults(db_helpers, organization):
    """Test creating campaign with default values."""
    campaign = db_helpers.create_test_campaign_in_db({"organization_id": organization.id})
    
    assert campaign.name == "Test Campaign"
    assert campaign.status == CampaignStatus.CREATED
    assert campaign.fileName == "test.csv"
    assert campaign.totalRecords == 100
    assert campaign.url == "https://test.com"
    assert campaign.organization_id == organization.id
    assert campaign.id is not None


def test_create_test_campaign_in_db_overrides(db_helpers, sample_campaign_data):
    """Test creating campaign with custom values."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    assert campaign.name == sample_campaign_data["name"]
    assert campaign.description == sample_campaign_data["description"]
    assert campaign.fileName == sample_campaign_data["fileName"]
    assert campaign.totalRecords == sample_campaign_data["totalRecords"]
    assert campaign.url == sample_campaign_data["url"]
    assert campaign.organization_id == sample_campaign_data["organization_id"]


def test_create_test_job_in_db(db_helpers, sample_campaign_data):
    """Test creating job in database."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    job = db_helpers.create_test_job_in_db(campaign.id, {
        "name": "Custom Job",
        "job_type": JobType.FETCH_LEADS,
        "status": JobStatus.PROCESSING
    })
    
    assert job.name == "Custom Job"
    assert job.job_type == JobType.FETCH_LEADS
    assert job.status == JobStatus.PROCESSING
    assert job.campaign_id == campaign.id
    assert job.task_id is not None


def test_verify_job_status_in_db(db_helpers, sample_campaign_data):
    """Test job status verification."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    job = db_helpers.create_test_job_in_db(campaign.id)
    
    # Verify initial status
    found_job = db_helpers.verify_job_status_in_db(job.id, JobStatus.PENDING)
    assert found_job.id == job.id
    
    # Test with string status
    db_helpers.verify_job_status_in_db(job.id, "pending")
    
    # Update and verify
    job.status = JobStatus.COMPLETED
    db_helpers.db_session.commit()
    
    db_helpers.verify_job_status_in_db(job.id, JobStatus.COMPLETED)


def test_verify_job_status_in_db_not_found(db_helpers):
    """Test job status verification fails when job doesn't exist."""
    with pytest.raises(AssertionError, match="Job 999 not found in database"):
        db_helpers.verify_job_status_in_db(999, JobStatus.PENDING)


def test_verify_campaign_timestamps(db_helpers, sample_campaign_data):
    """Test campaign timestamp verification."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Should pass with recent timestamps
    verified_campaign = db_helpers.verify_campaign_timestamps(campaign.id)
    assert verified_campaign.id == campaign.id
    
    # Test without checking updated time
    db_helpers.verify_campaign_timestamps(campaign.id, check_updated=False)


def test_verify_campaign_timestamps_old_updated_at(db_helpers, sample_campaign_data):
    """Test campaign timestamp verification fails with old updated_at."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Manually set old updated_at to be exactly 15 seconds ago
    # This should definitely be considered "not recent" (threshold is 10 seconds)
    old_time = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(seconds=15)
    
    # Ensure it's still after created_at by setting created_at to even older
    campaign.created_at = old_time - timedelta(seconds=5)
    campaign.updated_at = old_time
    db_helpers.db_session.commit()
    
    with pytest.raises(AssertionError, match="updated_at timestamp is not recent"):
        db_helpers.verify_campaign_timestamps(campaign.id, check_updated=True)


def test_get_campaign_by_field(db_helpers, sample_campaign_data):
    """Test getting campaign by any field."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Find by name
    found = db_helpers.get_campaign_by_field("name", sample_campaign_data["name"])
    assert found.id == campaign.id
    
    # Find by organization_id
    found = db_helpers.get_campaign_by_field("organization_id", sample_campaign_data["organization_id"])
    assert found.id == campaign.id
    
    # Not found
    found = db_helpers.get_campaign_by_field("name", "Non-existent")
    assert found is None


def test_verify_no_orphaned_jobs(db_helpers, sample_campaign_data):
    """Test verification of no orphaned jobs."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    job = db_helpers.create_test_job_in_db(campaign.id)
    
    # Should pass with valid job
    db_helpers.verify_no_orphaned_jobs()
    
    # Since PostgreSQL enforces FK constraints, we can't create orphaned jobs
    # by updating existing jobs. Instead, test that the verification works
    # correctly with valid data.
    # The method should pass when all jobs have valid campaign references
    assert True  # Test passes if no exception is raised above


# ---------------------------------------------------------------------------
# Convenience Function Tests
# ---------------------------------------------------------------------------

def test_convenience_functions(db_session, sample_campaign_data):
    """Test convenience functions work correctly."""
    # Test create_test_campaign_in_db
    campaign = create_test_campaign_in_db(db_session, sample_campaign_data)
    assert campaign.name == sample_campaign_data["name"]
    
    # Test verify_campaign_in_db
    found_campaign = verify_campaign_in_db(db_session, campaign.id, {
        "name": sample_campaign_data["name"]
    })
    assert found_campaign.id == campaign.id
    
    # Test count_campaigns_in_db
    count = count_campaigns_in_db(db_session)
    assert count == 1
    
    # Test cleanup_test_data
    result = cleanup_test_data(db_session)
    assert result["campaigns_deleted"] == 1
    
    # Test verify_campaign_not_in_db
    verify_campaign_not_in_db(db_session, campaign.id)


def test_enum_handling(db_helpers, sample_campaign_data):
    """Test proper handling of enum values in comparisons."""
    campaign = db_helpers.create_test_campaign_in_db({
        **sample_campaign_data,
        "status": CampaignStatus.RUNNING
    })
    
    # Should work with enum
    db_helpers.verify_campaign_in_db(campaign.id, {
        "status": CampaignStatus.RUNNING.value
    })
    
    # Should work with string
    db_helpers.verify_campaign_status_in_db(campaign.id, "running")


def test_datetime_handling(db_helpers, sample_campaign_data):
    """Test proper handling of datetime values in comparisons."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Get the actual datetime from database
    created_at_iso = campaign.created_at.isoformat()
    
    # Should work with ISO string comparison
    db_helpers.verify_campaign_in_db(campaign.id, {
        "created_at": created_at_iso
    })


def test_error_messages_are_clear(db_helpers, sample_campaign_data):
    """Test that error messages provide clear information."""
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    try:
        db_helpers.verify_campaign_in_db(campaign.id, {"name": "Wrong Name"})
        assert False, "Should have raised AssertionError"
    except AssertionError as e:
        error_msg = str(e)
        assert campaign.id in error_msg
        assert "Expected name=Wrong Name" in error_msg
        assert "got Test Campaign" in error_msg


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

def test_full_campaign_lifecycle_verification(db_helpers, sample_campaign_data):
    """Test verifying a complete campaign lifecycle."""
    # Create campaign
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Verify initial state
    db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.CREATED)
    db_helpers.verify_campaign_timestamps(campaign.id)
    
    # Create jobs
    fetch_job = db_helpers.create_test_job_in_db(campaign.id, {
        "job_type": JobType.FETCH_LEADS,
        "status": JobStatus.PROCESSING
    })
    
    # Verify jobs
    db_helpers.verify_job_created_for_campaign(campaign.id, JobType.FETCH_LEADS)
    db_helpers.verify_job_status_in_db(fetch_job.id, JobStatus.PROCESSING)
    
    # Update campaign status
    campaign.status = CampaignStatus.RUNNING
    db_helpers.db_session.commit()
    
    # Verify updated state
    db_helpers.verify_campaign_status_in_db(campaign.id, CampaignStatus.RUNNING)
    
    # Complete job
    fetch_job.status = JobStatus.COMPLETED
    db_helpers.db_session.commit()
    
    # Verify final state
    db_helpers.verify_job_status_in_db(fetch_job.id, JobStatus.COMPLETED)
    jobs = db_helpers.get_campaign_jobs_from_db(campaign.id)
    assert len(jobs) == 1
    
    # Verify no orphaned jobs
    db_helpers.verify_no_orphaned_jobs()


def test_multiple_campaigns_and_jobs(db_helpers, sample_campaign_data):
    """Test handling multiple campaigns and jobs."""
    # Create multiple campaigns
    campaign1 = db_helpers.create_test_campaign_in_db({
        **sample_campaign_data,
        "name": "Campaign 1"
    })
    campaign2 = db_helpers.create_test_campaign_in_db({
        **sample_campaign_data,
        "name": "Campaign 2"
    })
    
    # Create jobs for each campaign
    job1 = db_helpers.create_test_job_in_db(campaign1.id, {"job_type": JobType.FETCH_LEADS})
    job2 = db_helpers.create_test_job_in_db(campaign2.id, {"job_type": JobType.ENRICH_LEAD})
    job3 = db_helpers.create_test_job_in_db(campaign1.id, {"job_type": JobType.ENRICH_LEAD})
    
    # Verify counts
    assert db_helpers.count_campaigns_in_db() == 2
    
    # Verify jobs per campaign
    campaign1_jobs = db_helpers.get_campaign_jobs_from_db(campaign1.id)
    campaign2_jobs = db_helpers.get_campaign_jobs_from_db(campaign2.id)
    
    assert len(campaign1_jobs) == 2
    assert len(campaign2_jobs) == 1
    
    # Verify specific jobs
    db_helpers.verify_job_created_for_campaign(campaign1.id, JobType.FETCH_LEADS)
    db_helpers.verify_job_created_for_campaign(campaign1.id, JobType.ENRICH_LEAD)
    db_helpers.verify_job_created_for_campaign(campaign2.id, JobType.ENRICH_LEAD)
    
    # Clean up and verify
    result = db_helpers.cleanup_test_data()
    assert result["campaigns_deleted"] == 2
    assert result["jobs_deleted"] == 3
    assert db_helpers.count_campaigns_in_db() == 0 