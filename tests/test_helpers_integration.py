"""
Integration test demonstrating database helpers usage with campaign API tests.

This shows how the helpers can be used in real API testing scenarios.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from app.main import app
from app.core.database import Base, get_db
from tests.helpers.database_helpers import DatabaseHelpers
from tests.helpers.instantly_mock import mock_instantly_service

# Test database
# SQLALCHEMY_DATABASE_URL = "sqlite:///./test_helpers_integration.db"
# engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
# TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#
# Base.metadata.create_all(bind=engine)
#
# def override_get_db():
#     try:
#         db = TestingSessionLocal()
#         yield db
#     finally:
#         db.close()
#
# app.dependency_overrides[get_db] = override_get_db
#
# client = TestClient(app)

@pytest.fixture
def db_helpers(test_db_session):
    """Create DatabaseHelpers instance for testing."""
    return DatabaseHelpers(test_db_session)

@pytest.fixture(autouse=True, scope="module")
def mock_instantly_service():
    """Mock InstantlyService for all helpers integration tests."""
    class DummyInstantlyService:
        def __init__(self, *args, **kwargs):
            pass
        def create_lead(self, *args, **kwargs):
            return {"result": "mocked"}
        def create_campaign(self, *args, **kwargs):
            return {"id": "mocked-campaign-id"}
        def get_campaign_analytics_overview(self, *args, **kwargs):
            return {"analytics": "mocked"}
    with patch("app.services.campaign.InstantlyService", DummyInstantlyService):
        yield

def test_campaign_api_with_database_verification(db_helpers, organization, authenticated_client):
    """Test campaign API endpoints with comprehensive database verification."""
    
    # Initial state - no campaigns
    assert db_helpers.count_campaigns_in_db() == 0
    
    # Create campaign via API
    campaign_data = {
        "name": "API Test Campaign",
        "description": "Created via API",
        "fileName": "api_test.csv",
        "totalRecords": 150,
        "url": "https://api-test.com",
        "organization_id": organization.id
    }
    
    response = authenticated_client.post("/api/v1/campaigns/", json=campaign_data)
    assert response.status_code == 201
    
    response_data = response.json()
    
    # Check structured response format
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    api_campaign = response_data["data"]
    campaign_id = api_campaign["id"]
    
    # Verify campaign was created in database with correct values
    db_campaign = db_helpers.verify_campaign_in_db(campaign_id, {
        "name": campaign_data["name"],
        "description": campaign_data["description"],
        "fileName": campaign_data["fileName"],
        "totalRecords": campaign_data["totalRecords"],
        "url": campaign_data["url"],
        "organization_id": campaign_data["organization_id"],
        "status": "created"
    })
    
    # Verify timestamps are properly set
    db_helpers.verify_campaign_timestamps(campaign_id)
    
    # Verify count increased
    assert db_helpers.count_campaigns_in_db() == 1
    
    # Update campaign via API
    update_data = {"name": "Updated API Campaign", "description": "Updated via API"}
    response = authenticated_client.patch(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    assert response.status_code == 200
    
    # Verify updates in database
    db_helpers.verify_campaign_in_db(campaign_id, {
        "name": "Updated API Campaign",
        "description": "Updated via API"
    })
    
    # Verify timestamps were updated (but don't check if recent since it might be from different transaction)
    db_helpers.verify_campaign_timestamps(campaign_id, check_updated=False)
    
    # Get campaign via API and verify consistency
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 200
    
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    api_campaign = response_data["data"]
    assert api_campaign["name"] == "Updated API Campaign"
    assert api_campaign["description"] == "Updated via API"
    
    # Get fresh campaign from database for comparison
    updated_db_campaign = db_helpers.verify_campaign_in_db(campaign_id)
    
    # Verify API response matches database
    assert api_campaign["name"] == updated_db_campaign.name
    assert api_campaign["fileName"] == updated_db_campaign.fileName
    assert api_campaign["totalRecords"] == updated_db_campaign.totalRecords

def test_campaign_creation_with_job_verification(db_helpers, organization):
    """Test campaign creation and verify any background jobs are created."""
    
    # Create campaign directly in database for testing
    campaign = db_helpers.create_test_campaign_in_db({
        "name": "Job Test Campaign",
        "status": "created",
        "organization_id": organization.id
    })
    
    # Create a background job for the campaign
    job = db_helpers.create_test_job_in_db(campaign.id, {
        "name": "Test Background Job",
        "job_type": "FETCH_LEADS",
        "status": "PENDING"
    })
    
    # Verify job was created for campaign
    found_job = db_helpers.verify_job_created_for_campaign(campaign.id, "FETCH_LEADS")
    assert found_job.id == job.id
    
    # Verify job status
    db_helpers.verify_job_status_in_db(job.id, "PENDING")
    
    # Get all jobs for campaign
    jobs = db_helpers.get_campaign_jobs_from_db(campaign.id)
    assert len(jobs) == 1
    assert jobs[0].id == job.id
    
    # Update job status
    job.status = "COMPLETED"
    db_helpers.db_session.commit()
    
    # Verify status update
    db_helpers.verify_job_status_in_db(job.id, "COMPLETED")

def test_multiple_campaigns_database_state(db_helpers, organization, authenticated_client):
    """Test managing multiple campaigns and verifying database state."""
    
    # Create multiple campaigns via API
    campaigns = []
    for i in range(3):
        campaign_data = {
            "name": f"Multi Campaign {i+1}",
            "fileName": f"multi_{i+1}.csv",
            "totalRecords": (i+1) * 50,
            "url": f"https://multi-{i+1}.com",
            "organization_id": organization.id
        }
        
        response = authenticated_client.post("/api/v1/campaigns/", json=campaign_data)
        assert response.status_code == 201
        
        response_data = response.json()
        assert "status" in response_data
        assert "data" in response_data
        assert response_data["status"] == "success"
        
        campaigns.append(response_data["data"])
    
    # Verify count
    assert db_helpers.count_campaigns_in_db() == 3
    
    # Verify each campaign exists with correct data
    for i, campaign in enumerate(campaigns):
        db_helpers.verify_campaign_in_db(campaign["id"], {
            "name": f"Multi Campaign {i+1}",
            "totalRecords": (i+1) * 50
        })
    
    # Test campaign lookup by field
    campaign_1 = db_helpers.get_campaign_by_field("name", "Multi Campaign 1")
    assert campaign_1 is not None
    assert campaign_1.totalRecords == 50
    
    # Test non-existent campaign
    non_existent = db_helpers.get_campaign_by_field("name", "Non-existent Campaign")
    assert non_existent is None
    
    # Verify no orphaned jobs (should pass since we haven't created any jobs)
    db_helpers.verify_no_orphaned_jobs()

def test_error_handling_and_cleanup(db_helpers, organization):
    """Test error handling and cleanup functionality."""
    
    # Create test data
    campaign = db_helpers.create_test_campaign_in_db({
        "name": "Cleanup Test",
        "organization_id": organization.id
    })
    job = db_helpers.create_test_job_in_db(campaign.id)
    
    # Verify data exists
    assert db_helpers.count_campaigns_in_db() == 1
    jobs = db_helpers.get_campaign_jobs_from_db(campaign.id)
    assert len(jobs) == 1
    
    # Test error cases
    fake_id = "non-existent-id"
    
    # Should raise assertion error for non-existent campaign
    with pytest.raises(AssertionError):
        db_helpers.verify_campaign_in_db(fake_id)
    
    # Should raise assertion error for wrong values
    with pytest.raises(AssertionError):
        db_helpers.verify_campaign_in_db(campaign.id, {"name": "Wrong Name"})
    
    # Should raise assertion error for non-existent job
    with pytest.raises(AssertionError):
        db_helpers.verify_job_status_in_db(99999, "PENDING")
    
    # Clean up all test data
    result = db_helpers.cleanup_test_data()
    assert result["campaigns_deleted"] == 1
    assert result["jobs_deleted"] == 1
    
    # Verify cleanup worked
    assert db_helpers.count_campaigns_in_db() == 0
    
    # Should not raise error for non-existent campaign after cleanup
    db_helpers.verify_campaign_not_in_db(campaign.id) 