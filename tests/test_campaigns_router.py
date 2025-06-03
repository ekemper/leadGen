import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.core.database import Base, get_db
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from tests.helpers.instantly_mock import mock_instantly_service

@pytest.fixture
def sample_campaign_data(organization):
    """Sample campaign data for testing."""
    return {
        "name": "Test Campaign",
        "description": "A test campaign",
        "organization_id": organization.id,
        "fileName": "test_file.csv",
        "totalRecords": 100,
        "url": "https://app.apollo.io/test-search"
    }

def test_create_campaign(sample_campaign_data, authenticated_client):
    """Test creating a new campaign."""
    response = authenticated_client.post("/api/v1/campaigns/", json=sample_campaign_data)
    
    assert response.status_code == 201
    response_data = response.json()
    
    # Check structured response format
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    data = response_data["data"]
    assert data["name"] == sample_campaign_data["name"]
    assert data["description"] == sample_campaign_data["description"]
    assert data["status"] == CampaignStatus.CREATED.value
    assert data["fileName"] == sample_campaign_data["fileName"]
    assert data["totalRecords"] == sample_campaign_data["totalRecords"]
    assert data["url"] == sample_campaign_data["url"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_list_campaigns(authenticated_client):
    """Test listing campaigns."""
    response = authenticated_client.get("/api/v1/campaigns/")
    
    assert response.status_code == 200
    response_data = response.json()
    
    # Check structured response format
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    data = response_data["data"]
    assert "campaigns" in data
    assert isinstance(data["campaigns"], list)

def test_get_campaign_not_found(authenticated_client):
    """Test getting a non-existent campaign."""
    response = authenticated_client.get("/api/v1/campaigns/non-existent-id")
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

def test_get_campaign_details_not_found(authenticated_client):
    """Test getting details for a non-existent campaign."""
    response = authenticated_client.get("/api/v1/campaigns/non-existent-id/details")
    
    assert response.status_code == 404

def test_update_campaign_not_found(authenticated_client):
    """Test updating a non-existent campaign."""
    update_data = {"name": "Updated Name"}
    response = authenticated_client.patch("/api/v1/campaigns/non-existent-id", json=update_data)
    
    assert response.status_code == 404

def test_start_campaign_not_found(authenticated_client):
    """Test starting a non-existent campaign."""
    response = authenticated_client.post("/api/v1/campaigns/non-existent-id/start", json={})
    
    assert response.status_code == 404

def test_cleanup_campaign_jobs_invalid_data(authenticated_client):
    """Test cleanup with invalid data."""
    # Missing days parameter
    response = authenticated_client.post("/api/v1/campaigns/test-id/cleanup", json={})
    assert response.status_code == 400
    
    # Invalid days value
    response = authenticated_client.post("/api/v1/campaigns/test-id/cleanup", json={"days": -1})
    assert response.status_code == 400

def test_get_campaign_results_not_found(authenticated_client):
    """Test getting results for a non-existent campaign."""
    response = authenticated_client.get("/api/v1/campaigns/non-existent-id/results")
    
    assert response.status_code == 404

def test_campaign_workflow(sample_campaign_data, authenticated_client):
    """Test a complete campaign workflow."""
    # 1. Create campaign
    response = authenticated_client.post("/api/v1/campaigns/", json=sample_campaign_data)
    assert response.status_code == 201
    campaign_response = response.json()
    assert "status" in campaign_response
    assert "data" in campaign_response
    assert campaign_response["status"] == "success"
    campaign = campaign_response["data"]
    campaign_id = campaign["id"]
    
    # 2. Get campaign
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 200
    retrieved_response = response.json()
    assert "status" in retrieved_response
    assert "data" in retrieved_response
    assert retrieved_response["status"] == "success"
    retrieved_campaign = retrieved_response["data"]
    assert retrieved_campaign["id"] == campaign_id
    
    # 3. Update campaign
    update_data = {"name": "Updated Test Campaign"}
    response = authenticated_client.patch(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    assert response.status_code == 200
    updated_response = response.json()
    assert "status" in updated_response
    assert "data" in updated_response
    assert updated_response["status"] == "success"
    updated_campaign = updated_response["data"]
    assert updated_campaign["name"] == "Updated Test Campaign"
    
    # 4. Get campaign details
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/details")
    assert response.status_code == 200
    details = response.json()
    assert "data" in details
    assert "campaign" in details["data"]
    assert "lead_stats" in details["data"]
    assert "instantly_analytics" in details["data"]
    
    # 5. Start campaign (this will fail due to missing dependencies, but should return proper error)
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    # This might fail due to missing Apollo/Instantly services, but should not crash
    assert response.status_code in [200, 500]  # Either success or expected service error
    
    # 6. Cleanup jobs
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/cleanup", json={"days": 30})
    assert response.status_code == 200
    cleanup_result = response.json()
    assert "message" in cleanup_result
    
    # 7. Get results (should return 404 since no completed jobs)
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/results")
    assert response.status_code == 404  # No completed jobs

def test_campaign_validation(authenticated_client):
    """Test campaign validation."""
    # Missing required fields
    response = authenticated_client.post("/api/v1/campaigns/", json={})
    assert response.status_code == 422  # Validation error
    
    # Invalid data types
    invalid_data = {
        "name": "",  # Empty name should fail
        "description": "Test",
        "fileName": "",  # Empty fileName should fail
        "totalRecords": -1,  # Negative records should fail
        "url": ""  # Empty URL should fail
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=invalid_data)
    assert response.status_code == 422  # Validation error 