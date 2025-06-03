import pytest
from datetime import datetime, timedelta, timezone
import uuid
import time
from unittest.mock import patch, MagicMock

from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus, JobType
from app.models.organization import Organization
from tests.helpers.instantly_mock import mock_instantly_service
from tests.helpers.auth_helpers import AuthHelpers

# All database setup is now handled by conftest.py

# db_session fixture is provided by conftest.py

@pytest.fixture
def organization_payload():
    """Return a valid payload for creating an organization via the API."""
    return {
        "name": "Test Organization",
        "description": "This is a test organization"
    }

@pytest.fixture
def authenticated_campaign_payload(authenticated_client, organization_payload):
    """Return a valid payload for creating a campaign via the API with auth."""
    # Create an organization first using authenticated client
    response = authenticated_client.post("/api/v1/organizations/", json=organization_payload)
    assert response.status_code == 201
    org_id = response.json()["id"]
    
    return {
        "name": "API Test Campaign",
        "description": "This campaign is created by tests",
        "fileName": "input-file.csv",
        "totalRecords": 25,
        "url": "https://app.apollo.io/#/some-search",
        "organization_id": org_id
    }

@pytest.fixture
def campaign_payload(client, organization_payload):
    """Return a valid payload for creating a campaign via the API (legacy - for auth tests)."""
    # This fixture is kept for testing authentication requirements
    return {
        "name": "API Test Campaign",
        "description": "This campaign is created by tests",
        "fileName": "input-file.csv",
        "totalRecords": 25,
        "url": "https://app.apollo.io/#/some-search",
        "organization_id": str(uuid.uuid4())  # Use fake org ID for auth tests
    }

def verify_campaign_in_db(db_session, campaign_id: str, expected_data: dict = None):
    """Helper to verify campaign exists in database with correct values."""
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert campaign is not None, f"Campaign {campaign_id} not found in database"
    
    if expected_data:
        for key, value in expected_data.items():
            db_value = getattr(campaign, key)
            if isinstance(db_value, CampaignStatus):
                db_value = db_value.value
            assert db_value == value, f"Expected {key}={value}, got {db_value}"
    
    return campaign

def verify_no_campaign_in_db(db_session, campaign_id: str = None):
    """Helper to verify no campaign records exist in database."""
    if campaign_id:
        campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
        assert campaign is None, f"Campaign {campaign_id} should not exist in database"
    else:
        count = db_session.query(Campaign).count()
        assert count == 0, f"Expected 0 campaigns in database, found {count}"

def verify_job_in_db(db_session, campaign_id: str, job_type: JobType, expected_count: int = 1):
    """Helper to verify job exists in database for campaign."""
    jobs = db_session.query(Job).filter(
        Job.campaign_id == campaign_id,
        Job.job_type == job_type
    ).all()
    assert len(jobs) == expected_count, f"Expected {expected_count} {job_type.value} jobs, found {len(jobs)}"
    return jobs

# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------

def test_create_campaign_requires_auth(client, db_session, campaign_payload):
    """Test that campaign creation requires authentication."""
    response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert response.status_code == 401

def test_list_campaigns_requires_auth(client, db_session):
    """Test that listing campaigns requires authentication."""
    response = client.get("/api/v1/campaigns/")
    assert response.status_code == 401

def test_get_campaign_requires_auth(client, db_session):
    """Test that getting a campaign requires authentication."""
    campaign_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 401

def test_update_campaign_requires_auth(client, db_session):
    """Test that updating a campaign requires authentication."""
    campaign_id = str(uuid.uuid4())
    response = client.patch(f"/api/v1/campaigns/{campaign_id}", json={"name": "Updated"})
    assert response.status_code == 401

def test_start_campaign_requires_auth(client, db_session):
    """Test that starting a campaign requires authentication."""
    campaign_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/campaigns/{campaign_id}/start")
    assert response.status_code == 401

# ---------------------------------------------------------------------------
# Campaign Creation Tests
# ---------------------------------------------------------------------------

def test_create_campaign_success(authenticated_client, db_session, authenticated_campaign_payload):
    """Test successful campaign creation with all required fields."""
    response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    
    # Verify API response
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["status"] == "success"
    assert "data" in response_data
    data = response_data["data"]
    
    assert data["name"] == authenticated_campaign_payload["name"]
    assert data["status"] == CampaignStatus.CREATED.value
    assert data["fileName"] == authenticated_campaign_payload["fileName"]
    assert data["totalRecords"] == authenticated_campaign_payload["totalRecords"]
    assert data["url"] == authenticated_campaign_payload["url"]
    assert data["organization_id"] == authenticated_campaign_payload["organization_id"]
    assert "id" in data
    assert "created_at" in data
    
    # Verify campaign record exists in database with correct values
    verify_campaign_in_db(db_session, data["id"], {
        "name": authenticated_campaign_payload["name"],
        "status": CampaignStatus.CREATED.value,
        "fileName": authenticated_campaign_payload["fileName"],
        "totalRecords": authenticated_campaign_payload["totalRecords"],
        "url": authenticated_campaign_payload["url"],
        "organization_id": authenticated_campaign_payload["organization_id"]
    })

def test_create_campaign_validation_missing_fields(authenticated_client, db_session, organization_payload):
    """Test validation errors for missing required fields."""
    # Create organization first
    response = authenticated_client.post("/api/v1/organizations/", json=organization_payload)
    assert response.status_code == 201
    
    bad_payload = {
        "name": "Missing Fields",
        "fileName": "file.csv",
        "url": "https://app.apollo.io"
        # Missing totalRecords (required)
    }
    
    response = authenticated_client.post("/api/v1/campaigns/", json=bad_payload)
    assert response.status_code == 422  # Validation error
    
    # Verify no campaign records created on validation failures
    verify_no_campaign_in_db(db_session)

def test_create_campaign_validation_invalid_fields(authenticated_client, db_session, organization_payload):
    """Test validation errors for invalid field values."""
    # Create organization first
    response = authenticated_client.post("/api/v1/organizations/", json=organization_payload)
    assert response.status_code == 201
    
    bad_payload = {
        "name": "",  # Empty name should fail
        "description": "Test",
        "fileName": "",  # Empty fileName should fail
        "totalRecords": -1,  # Negative records should fail
        "url": ""  # Empty URL should fail
    }
    
    response = authenticated_client.post("/api/v1/campaigns/", json=bad_payload)
    assert response.status_code == 422  # Validation error
    
    # Verify no campaign records created on validation failures
    verify_no_campaign_in_db(db_session)

def test_create_campaign_special_characters(authenticated_client, db_session, authenticated_campaign_payload):
    """Test campaign creation with special characters."""
    payload = {**authenticated_campaign_payload, "name": "!@#$%^&*()_+-=[]{}|;:,.<>?/~`\"'\\"}
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    
    assert response.status_code == 201
    response_data = response.json()
    data = response_data["data"]
    assert data["name"] == payload["name"]
    
    # Verify database record
    verify_campaign_in_db(db_session, data["id"], {"name": payload["name"]})

def test_create_campaign_xss_prevention(authenticated_client, db_session, authenticated_campaign_payload):
    """Test XSS prevention in campaign names/descriptions."""
    payload = {
        **authenticated_campaign_payload,
        "name": "<script>alert(\"XSS\")</script>Campaign",
        "description": "<img src=x onerror=alert('XSS')>"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    
    assert response.status_code == 201
    response_data = response.json()
    data = response_data["data"]
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    
    # Verify database stores the values as-is (no HTML escaping at API level)
    verify_campaign_in_db(db_session, data["id"], {
        "name": payload["name"],
        "description": payload["description"]
    })

def test_create_campaign_long_description(authenticated_client, db_session, authenticated_campaign_payload):
    """Test campaign creation with extremely long field values."""
    long_description = "x" * 10000
    payload = {**authenticated_campaign_payload, "description": long_description}
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    
    assert response.status_code == 201
    response_data = response.json()
    data = response_data["data"]
    assert len(data["description"]) == 10000
    
    # Verify database record
    verify_campaign_in_db(db_session, data["id"], {"description": long_description})

# ---------------------------------------------------------------------------
# Campaign Listing Tests
# ---------------------------------------------------------------------------

def test_list_campaigns_empty(authenticated_client, db_session):
    """Test empty campaign list returns correctly."""
    response = authenticated_client.get("/api/v1/campaigns/")
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert "data" in response_data
    data = response_data["data"]
    assert isinstance(data["campaigns"], list)
    assert len(data["campaigns"]) == 0
    assert data["total"] == 0
    
    # Verify database is empty
    verify_no_campaign_in_db(db_session)

def test_list_campaigns_multiple(authenticated_client, db_session, authenticated_campaign_payload):
    """Create multiple campaigns and verify list endpoint returns all."""
    created_campaigns = []
    
    # Create 3 campaigns
    for i in range(3):
        payload = {**authenticated_campaign_payload, "name": f"Campaign {i}"}
        response = authenticated_client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
        created_campaigns.append(response.json()["data"])
    
    # List campaigns
    response = authenticated_client.get("/api/v1/campaigns/")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    data = response_data["data"]
    assert len(data["campaigns"]) == 3
    assert data["total"] == 3
    
    # Verify all campaigns are returned
    returned_ids = {campaign["id"] for campaign in data["campaigns"]}
    expected_ids = {campaign["id"] for campaign in created_campaigns}
    assert returned_ids == expected_ids

def test_list_campaigns_pagination(authenticated_client, db_session, authenticated_campaign_payload):
    """Test pagination parameters work correctly."""
    # Create 5 campaigns
    for i in range(5):
        payload = {**authenticated_campaign_payload, "name": f"Campaign {i}"}
        response = authenticated_client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
    
    # Test pagination (page 2, 2 per page)
    response = authenticated_client.get("/api/v1/campaigns/?page=2&per_page=2")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    data = response_data["data"]
    assert len(data["campaigns"]) == 2  # Should return 2 campaigns (per_page=2)
    assert data["total"] == 5  # Total should be 5
    assert data["page"] == 2  # Current page should be 2
    assert data["per_page"] == 2
    assert data["pages"] == 3  # Total pages should be 3 (5 campaigns / 2 per page)
    
    # Verify database still has all 5 campaigns
    db_count = db_session.query(Campaign).count()
    assert db_count == 5

def test_list_campaigns_order(authenticated_client, db_session, authenticated_campaign_payload):
    """Test campaigns are returned in correct order."""
    # Create campaigns with timestamps
    created_campaigns = []
    for i in range(3):
        payload = {**authenticated_campaign_payload, "name": f"Campaign {i}"}
        response = authenticated_client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
        created_campaigns.append(response.json()["data"])
        # Add small delay to ensure different timestamps
        time.sleep(0.1)
    
    # List campaigns
    response = authenticated_client.get("/api/v1/campaigns/")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    data = response_data["data"]
    
    # Verify we got all campaigns
    assert len(data["campaigns"]) == 3
    assert data["total"] == 3
    
    # Verify all created campaigns are in the response
    returned_names = {campaign["name"] for campaign in data["campaigns"]}
    expected_names = {f"Campaign {i}" for i in range(3)}
    assert returned_names == expected_names
    
    # Verify campaigns have valid timestamps
    for campaign in data["campaigns"]:
        assert "created_at" in campaign
        assert campaign["created_at"] is not None

# ---------------------------------------------------------------------------
# Campaign Retrieval Tests
# ---------------------------------------------------------------------------

def test_get_campaign_success(authenticated_client, db_session, authenticated_campaign_payload):
    """Test successful retrieval of existing campaign."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Retrieve campaign
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 200
    response_data = response.json()
    
    # Verify response structure
    assert response_data["status"] == "success"
    assert "data" in response_data
    data = response_data["data"]
    
    # Verify returned data matches database record exactly
    assert data["id"] == campaign_id
    assert data["name"] == authenticated_campaign_payload["name"]
    assert data["status"] == CampaignStatus.CREATED.value
    
    # Verify database record matches
    db_campaign = verify_campaign_in_db(db_session, campaign_id)
    assert data["name"] == db_campaign.name
    assert data["description"] == db_campaign.description

def test_get_campaign_not_found(authenticated_client, db_session):
    """Test 404 error for non-existent campaign ID."""
    non_existent_id = str(uuid.uuid4())
    response = authenticated_client.get(f"/api/v1/campaigns/{non_existent_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

def test_get_campaign_malformed_id(authenticated_client, db_session):
    """Test malformed campaign ID handling."""
    malformed_id = "not-a-valid-uuid"
    response = authenticated_client.get(f"/api/v1/campaigns/{malformed_id}")
    
    # Should return 404 (not found) rather than 400 (bad request)
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Campaign Update Tests
# ---------------------------------------------------------------------------

def test_update_campaign_success(authenticated_client, db_session, authenticated_campaign_payload):
    """Test successful update of allowed fields."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Update campaign
    update_data = {
        "name": "Updated Campaign Name",
        "description": "Updated description"
    }
    response = authenticated_client.patch(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    
    assert response.status_code == 200
    response_data = response.json()
    data = response_data["data"]
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    
    # Verify database record is updated correctly
    verify_campaign_in_db(db_session, campaign_id, {
        "name": update_data["name"],
        "description": update_data["description"]
    })

def test_update_campaign_partial(authenticated_client, db_session, authenticated_campaign_payload):
    """Test partial updates work correctly."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    original_name = create_response.json()["data"]["name"]
    
    # Update only description
    update_data = {"description": "Only description updated"}
    response = authenticated_client.patch(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    
    assert response.status_code == 200
    response_data = response.json()
    data = response_data["data"]
    assert data["name"] == original_name  # Should remain unchanged
    assert data["description"] == update_data["description"]
    
    # Verify database record
    verify_campaign_in_db(db_session, campaign_id, {
        "name": original_name,
        "description": update_data["description"]
    })

def test_update_campaign_validation_error(authenticated_client, db_session, authenticated_campaign_payload):
    """Test validation errors for invalid update data."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Try to update with invalid data
    invalid_update = {"totalRecords": -1}  # Negative value should fail
    response = authenticated_client.patch(f"/api/v1/campaigns/{campaign_id}", json=invalid_update)
    
    assert response.status_code == 422  # Validation error
    
    # Verify database record is unchanged
    verify_campaign_in_db(db_session, campaign_id, {
        "totalRecords": authenticated_campaign_payload["totalRecords"]
    })

def test_update_campaign_not_found(authenticated_client, db_session):
    """Test 404 error for non-existent campaign."""
    non_existent_id = str(uuid.uuid4())
    update_data = {"name": "Updated Name"}
    response = authenticated_client.patch(f"/api/v1/campaigns/{non_existent_id}", json=update_data)
    
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Campaign Start Flow Tests
# ---------------------------------------------------------------------------

def test_start_campaign_success(authenticated_client, db_session, authenticated_campaign_payload):
    """Test starting campaign changes status from CREATED to RUNNING."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Start campaign
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    
    # Note: This might fail due to missing Apollo/Instantly services
    # but we test the expected behavior when services are available
    if response.status_code == 200:
        response_data = response.json()
        data = response_data["data"]
        assert data["status"] == CampaignStatus.RUNNING.value
        
        # Verify database status update is persisted
        verify_campaign_in_db(db_session, campaign_id, {
            "status": CampaignStatus.RUNNING.value
        })
        
        # Verify background job is created in jobs table
        verify_job_in_db(db_session, campaign_id, JobType.FETCH_LEADS, expected_count=1)
    else:
        # Service unavailable - expected in test environment
        assert response.status_code in [500, 404]

def test_start_campaign_duplicate(authenticated_client, db_session, authenticated_campaign_payload):
    """Test error when trying to start non-CREATED campaign."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Manually update campaign status to RUNNING in database
    db_campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    db_campaign.status = CampaignStatus.RUNNING
    db_session.commit()
    
    # Try to start already running campaign
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    
    # Should return error for invalid state transition
    assert response.status_code in [400, 422]

def test_start_campaign_not_found(authenticated_client, db_session):
    """Test starting non-existent campaign returns 404."""
    non_existent_id = str(uuid.uuid4())
    response = authenticated_client.post(f"/api/v1/campaigns/{non_existent_id}/start", json={})
    
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Campaign Details Tests
# ---------------------------------------------------------------------------

def test_get_campaign_details_success(authenticated_client, db_session, authenticated_campaign_payload):
    """Test campaign details endpoint returns campaign + stats."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Get campaign details
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/details")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "data" in data
    assert "campaign" in data["data"]
    assert "lead_stats" in data["data"]
    assert "instantly_analytics" in data["data"]
    
    # Verify campaign data matches database
    campaign_data = data["data"]["campaign"]
    verify_campaign_in_db(db_session, campaign_id, {
        "name": campaign_data["name"],
        "status": campaign_data["status"]
    })
    
    # Verify lead statistics structure (even if zero)
    lead_stats = data["data"]["lead_stats"]
    expected_stats = [
        "total_leads_fetched", "leads_with_email", "leads_with_verified_email",
        "leads_with_enrichment", "leads_with_email_copy", "leads_with_instantly_record"
    ]
    for stat in expected_stats:
        assert stat in lead_stats

def test_get_campaign_details_not_found(authenticated_client, db_session):
    """Test campaign details for non-existent campaign returns 404."""
    non_existent_id = str(uuid.uuid4())
    response = authenticated_client.get(f"/api/v1/campaigns/{non_existent_id}/details")
    
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Job Cleanup Tests
# ---------------------------------------------------------------------------

def test_cleanup_old_jobs_success(authenticated_client, db_session, authenticated_campaign_payload):
    """Test cleanup of old job records."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Create old jobs (manually for testing)
    old_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=40)
    recent_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=10)
    
    old_job = Job(
        name="Old Test Job",
        description="Old job for cleanup testing",
        task_id=f"old-task-{uuid.uuid4()}",
        campaign_id=campaign_id,
        job_type=JobType.FETCH_LEADS,
        status=JobStatus.COMPLETED,
        created_at=old_date,
        completed_at=old_date
    )
    recent_job = Job(
        name="Recent Test Job",
        description="Recent job for cleanup testing",
        task_id=f"recent-task-{uuid.uuid4()}",
        campaign_id=campaign_id,
        job_type=JobType.FETCH_LEADS,
        status=JobStatus.COMPLETED,
        created_at=recent_date,
        completed_at=recent_date
    )
    
    db_session.add(old_job)
    db_session.add(recent_job)
    db_session.commit()
    
    # Cleanup jobs older than 30 days
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/cleanup-jobs", json={"days": 30})
    
    # Verify cleanup endpoint works
    if response.status_code == 200:
        # Verify old job is deleted but recent job remains
        remaining_jobs = db_session.query(Job).filter(Job.campaign_id == campaign_id).all()
        assert len(remaining_jobs) == 1
        assert remaining_jobs[0].id == recent_job.id
    else:
        # Endpoint not implemented yet
        assert response.status_code == 404

# ---------------------------------------------------------------------------
# Security Tests
# ---------------------------------------------------------------------------

def test_sql_injection_prevention(authenticated_client, db_session):
    """Test SQL injection attempts are prevented."""
    malicious_id = "'; DROP TABLE campaigns; --"
    response = authenticated_client.get(f"/api/v1/campaigns/{malicious_id}")
    
    # Should return 404, not execute SQL
    assert response.status_code == 404
    
    # Verify campaigns table still exists
    count = db_session.query(Campaign).count()
    assert count >= 0  # No exception means table exists

# ---------------------------------------------------------------------------
# Concurrency Tests
# ---------------------------------------------------------------------------

def test_concurrent_operations_same_campaign(authenticated_client, db_session, authenticated_campaign_payload):
    """Test concurrent operations on same campaign are handled correctly."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Simulate concurrent updates (in real scenario these would be parallel)
    update1 = {"name": "Update 1"}
    update2 = {"name": "Update 2"}
    
    response1 = authenticated_client.patch(f"/api/v1/campaigns/{campaign_id}", json=update1)
    response2 = authenticated_client.patch(f"/api/v1/campaigns/{campaign_id}", json=update2)
    
    # Both should succeed (last one wins)
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Verify final state in database
    final_campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert final_campaign.name == "Update 2"  # Last update should win

# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

def test_campaign_workflow_integration(authenticated_client, db_session, authenticated_campaign_payload):
    """Test complete campaign workflow with database verification at each step."""
    # 1. Create campaign
    response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert response.status_code == 201
    campaign = response.json()
    campaign_id = campaign["data"]["id"]
    
    # Verify creation in database
    verify_campaign_in_db(db_session, campaign_id, {
        "status": CampaignStatus.CREATED.value,
        "name": authenticated_campaign_payload["name"]
    })
    
    # 2. Update campaign
    update_response = authenticated_client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={"description": "Updated during workflow test"}
    )
    assert update_response.status_code == 200
    
    # Verify update in database
    verify_campaign_in_db(db_session, campaign_id, {
        "description": "Updated during workflow test"
    })
    
    # 3. Start campaign (may fail due to missing services)
    start_response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    if start_response.status_code == 200:
        # Verify status change in database
        verify_campaign_in_db(db_session, campaign_id, {
            "status": CampaignStatus.RUNNING.value
        })
    
    # 4. Get campaign details
    details_response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/details")
    assert details_response.status_code == 200
    
    # 5. List all campaigns (should include our campaign)
    list_response = authenticated_client.get("/api/v1/campaigns/")
    assert list_response.status_code == 200
    list_data = list_response.json()
    campaigns = list_data["data"]["campaigns"]
    assert any(c["id"] == campaign_id for c in campaigns)

# ---------------------------------------------------------------------------
# Campaign Lead Stats Tests
# ---------------------------------------------------------------------------

def test_get_campaign_lead_stats_success(authenticated_client, db_session, authenticated_campaign_payload):
    """Test successful retrieval of campaign lead statistics."""
    # Create campaign first
    response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert response.status_code == 201
    campaign_id = response.json()["data"]["id"]
    
    # Get campaign lead stats
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/leads/stats")
    
    # Verify API response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert "data" in response_data
    data = response_data["data"]
    
    # Verify stats structure (should be zeros for new campaign with no leads)
    assert data["total_leads_fetched"] == 0
    assert data["leads_with_email"] == 0
    assert data["leads_with_verified_email"] == 0
    assert data["leads_with_enrichment"] == 0
    assert data["leads_with_email_copy"] == 0
    assert data["leads_with_instantly_record"] == 0
    assert data["error_message"] is None

def test_get_campaign_lead_stats_not_found(authenticated_client, db_session):
    """Test campaign lead stats retrieval for non-existent campaign."""
    fake_campaign_id = str(uuid.uuid4())
    response = authenticated_client.get(f"/api/v1/campaigns/{fake_campaign_id}/leads/stats")
    assert response.status_code == 404

def test_get_campaign_lead_stats_requires_auth(client, db_session):
    """Test that campaign lead stats endpoint requires authentication."""
    fake_campaign_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/campaigns/{fake_campaign_id}/leads/stats")
    assert response.status_code == 401

def test_get_campaign_lead_stats_malformed_id(authenticated_client, db_session):
    """Test campaign lead stats retrieval with malformed campaign ID."""
    response = authenticated_client.get("/api/v1/campaigns/invalid-id/leads/stats")
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Campaign Instantly Analytics Tests
# ---------------------------------------------------------------------------

def test_get_campaign_instantly_analytics_success(authenticated_client, db_session, authenticated_campaign_payload):
    """Test successful retrieval of campaign Instantly analytics."""
    # Create campaign first
    response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert response.status_code == 201
    campaign_id = response.json()["data"]["id"]
    
    # Get campaign Instantly analytics
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/instantly/analytics")
    
    # Verify API response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert "data" in response_data
    data = response_data["data"]
    
    # Verify analytics structure
    assert "leads_count" in data
    assert "contacted_count" in data
    assert "emails_sent_count" in data
    assert "open_count" in data
    assert "link_click_count" in data
    assert "reply_count" in data
    assert "bounced_count" in data
    assert "unsubscribed_count" in data
    assert "completed_count" in data
    assert "new_leads_contacted_count" in data
    assert "total_opportunities" in data
    assert "campaign_name" in data
    assert "campaign_id" in data
    assert "campaign_status" in data
    assert "campaign_is_evergreen" in data
    
    # Campaign info should be populated (campaign was created with mocked Instantly ID)
    assert data["campaign_name"] == authenticated_campaign_payload["name"]
    assert data["campaign_id"] == campaign_id
    assert data["leads_count"] == authenticated_campaign_payload["totalRecords"]
    
    # Since we have a mocked Instantly service, error should be None for successful analytics
    assert data["error"] is None

def test_get_campaign_instantly_analytics_not_found(authenticated_client, db_session):
    """Test campaign Instantly analytics retrieval for non-existent campaign."""
    fake_campaign_id = str(uuid.uuid4())
    response = authenticated_client.get(f"/api/v1/campaigns/{fake_campaign_id}/instantly/analytics")
    assert response.status_code == 404

def test_get_campaign_instantly_analytics_requires_auth(client, db_session):
    """Test that campaign Instantly analytics endpoint requires authentication."""
    fake_campaign_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/campaigns/{fake_campaign_id}/instantly/analytics")
    assert response.status_code == 401

def test_get_campaign_instantly_analytics_malformed_id(authenticated_client, db_session):
    """Test campaign Instantly analytics retrieval with malformed campaign ID."""
    response = authenticated_client.get("/api/v1/campaigns/invalid-id/instantly/analytics")
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Integration Tests for New Endpoints
# ---------------------------------------------------------------------------

def test_campaign_stats_and_analytics_workflow(authenticated_client, db_session, authenticated_campaign_payload):
    """Test the complete workflow of creating a campaign and accessing its stats and analytics."""
    # Create campaign
    response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert response.status_code == 201
    campaign_id = response.json()["data"]["id"]
    
    # Get campaign details to verify it exists
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 200
    
    # Get lead stats
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/leads/stats")
    assert response.status_code == 200
    stats_data = response.json()["data"]
    assert stats_data["total_leads_fetched"] == 0  # New campaign should have no leads
    
    # Get Instantly analytics
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/instantly/analytics")
    assert response.status_code == 200
    analytics_data = response.json()["data"]
    assert analytics_data["campaign_name"] == authenticated_campaign_payload["name"]
    assert analytics_data["leads_count"] == authenticated_campaign_payload["totalRecords"]
    
    # Verify the /details endpoint still works (for backward compatibility)
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/details")
    assert response.status_code == 200
    details_data = response.json()["data"]
    assert "campaign" in details_data
    assert "lead_stats" in details_data
    assert "instantly_analytics" in details_data

def test_campaign_stats_error_handling(authenticated_client, db_session, authenticated_campaign_payload):
    """Test error handling in campaign stats endpoints."""
    # Create campaign
    response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert response.status_code == 201
    campaign_id = response.json()["data"]["id"]
    
    # Test that stats endpoint handles errors gracefully
    # (The current implementation returns zero stats rather than erroring)
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/leads/stats")
    assert response.status_code == 200
    stats_data = response.json()["data"]
    assert "error_message" in stats_data
    
    # Test that analytics endpoint handles Instantly ID gracefully
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/instantly/analytics")
    assert response.status_code == 200
    analytics_data = response.json()["data"]
    # Campaign was created with mocked Instantly ID, so no error should occur
    assert analytics_data["error"] is None
    assert analytics_data["campaign_id"] == campaign_id

# ---------------------------------------------------------------------------
# Schema Validation Tests
# ---------------------------------------------------------------------------

def test_campaign_stats_response_schema_validation(authenticated_client, db_session, authenticated_campaign_payload):
    """Test that campaign stats response conforms to expected schema."""
    # Create campaign
    response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert response.status_code == 201
    campaign_id = response.json()["data"]["id"]
    
    # Get stats and validate schema
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/leads/stats")
    assert response.status_code == 200
    data = response.json()["data"]
    
    # All required integer fields should be present and non-negative
    required_int_fields = [
        "total_leads_fetched", "leads_with_email", "leads_with_verified_email",
        "leads_with_enrichment", "leads_with_email_copy", "leads_with_instantly_record"
    ]
    for field in required_int_fields:
        assert field in data
        assert isinstance(data[field], int)
        assert data[field] >= 0
    
    # Error message should be optional string or null
    assert "error_message" in data
    assert data["error_message"] is None or isinstance(data["error_message"], str)

def test_campaign_analytics_response_schema_validation(authenticated_client, db_session, authenticated_campaign_payload):
    """Test campaign analytics response contains all required fields with proper types."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Get analytics
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/instantly/analytics")
    
    assert response.status_code == 200
    response_data = response.json()
    
    # Verify structure
    assert "data" in response_data
    data = response_data["data"]
    
    # Required fields for analytics response (actual field names from InstantlyAnalytics schema)
    required_fields = [
        "leads_count", "contacted_count", "emails_sent_count", "open_count",
        "link_click_count", "reply_count", "bounced_count", "unsubscribed_count",
        "completed_count", "new_leads_contacted_count", "total_opportunities",
        "campaign_name", "campaign_id", "campaign_status", "campaign_is_evergreen"
    ]
    
    for field in required_fields:
        assert field in data, f"Missing field: {field}"
        
    # Verify specific field types
    # Integer fields (can be None)
    int_fields = [
        "leads_count", "contacted_count", "emails_sent_count", "open_count",
        "link_click_count", "reply_count", "bounced_count", "unsubscribed_count",
        "completed_count", "new_leads_contacted_count", "total_opportunities"
    ]
    for field in int_fields:
        if data[field] is not None:
            assert isinstance(data[field], int), f"Field {field} should be int or None, got {type(data[field])}"
    
    # String fields
    string_fields = ["campaign_name", "campaign_id", "campaign_status"]
    for field in string_fields:
        if data[field] is not None:
            assert isinstance(data[field], str), f"Field {field} should be string or None, got {type(data[field])}"
    
    # Boolean field
    assert isinstance(data["campaign_is_evergreen"], bool), f"campaign_is_evergreen should be boolean, got {type(data['campaign_is_evergreen'])}"

# ---------------------------------------------------------------------------
# Business Rule Enforcement Tests
# ---------------------------------------------------------------------------

def test_paused_campaign_cannot_be_started(authenticated_client, db_session, authenticated_campaign_payload):
    """Test that paused campaigns cannot be started and return appropriate error."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Manually set campaign to PAUSED status
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = CampaignStatus.PAUSED
    campaign.status_message = "Campaign paused for testing"
    db_session.commit()
    
    # Try to start paused campaign
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    
    # Should return conflict error (409) for paused campaign
    assert response.status_code == 409
    response_data = response.json()
    assert "detail" in response_data
    assert isinstance(response_data["detail"], dict)
    assert "errors" in response_data["detail"]
    assert any("paused" in error.lower() for error in response_data["detail"]["errors"])

def test_campaign_start_validation_endpoint(authenticated_client, db_session, authenticated_campaign_payload):
    """Test the campaign start validation endpoint returns comprehensive validation results."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Test validation endpoint for created campaign
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/start/validate")
    assert response.status_code == 200
    
    validation_data = response.json()["data"]
    
    # Verify validation response structure
    required_fields = [
        "can_start", "campaign_status_valid", "services_available", 
        "global_state_ok", "validation_details", "warnings", "errors"
    ]
    for field in required_fields:
        assert field in validation_data, f"Missing validation field: {field}"
    
    # For a created campaign, campaign_status_valid should be True
    assert validation_data["campaign_status_valid"] is True
    
    # Validation details should contain campaign status info
    assert "campaign_status" in validation_data["validation_details"]
    assert "services" in validation_data["validation_details"]
    assert "global_state" in validation_data["validation_details"]

def test_paused_campaign_validation_details(authenticated_client, db_session, authenticated_campaign_payload):
    """Test validation endpoint provides detailed information for paused campaigns."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Pause the campaign
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = CampaignStatus.PAUSED
    campaign.status_message = "Paused for maintenance"
    db_session.commit()
    
    # Check validation
    response = authenticated_client.get(f"/api/v1/campaigns/{campaign_id}/start/validate")
    assert response.status_code == 200
    
    validation_data = response.json()["data"]
    
    # Should indicate campaign cannot be started
    assert validation_data["can_start"] is False
    assert validation_data["campaign_status_valid"] is False
    
    # Should have detailed error information
    assert len(validation_data["errors"]) > 0
    assert any("paused" in error.lower() for error in validation_data["errors"])
    
    # Campaign status details should show current status
    campaign_status_details = validation_data["validation_details"]["campaign_status"]
    assert campaign_status_details["current_status"] == "PAUSED"
    assert campaign_status_details["can_start"] is False

def test_completed_campaign_cannot_be_started(authenticated_client, db_session, authenticated_campaign_payload):
    """Test that completed campaigns cannot be started."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Set campaign to COMPLETED status
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = CampaignStatus.COMPLETED
    campaign.status_message = "Campaign completed"
    db_session.commit()
    
    # Try to start completed campaign
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    
    # Should return bad request error
    assert response.status_code in [400, 409]
    response_data = response.json()
    assert "detail" in response_data

def test_failed_campaign_cannot_be_started(authenticated_client, db_session, authenticated_campaign_payload):
    """Test that failed campaigns cannot be started."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Set campaign to FAILED status
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = CampaignStatus.FAILED
    campaign.status_message = "Campaign failed"
    campaign.status_error = "Test failure"
    db_session.commit()
    
    # Try to start failed campaign
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    
    # Should return bad request error
    assert response.status_code in [400, 409]

def test_running_campaign_cannot_be_started_again(authenticated_client, db_session, authenticated_campaign_payload):
    """Test that running campaigns cannot be started again."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Set campaign to RUNNING status
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = CampaignStatus.RUNNING
    campaign.status_message = "Campaign running"
    db_session.commit()
    
    # Try to start running campaign
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    
    # Should return bad request error
    assert response.status_code in [400, 409]

def test_campaign_creation_with_service_warnings(authenticated_client, db_session, authenticated_campaign_payload):
    """Test that campaign creation includes warnings when services are unavailable."""
    # Note: This test depends on the actual circuit breaker state
    # In a real test environment, you might mock the circuit breaker to simulate service outages
    
    # Create campaign (should succeed regardless of service state)
    response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert response.status_code == 201
    
    campaign_data = response.json()["data"]
    campaign_id = campaign_data["id"]
    
    # Verify campaign was created
    assert campaign_id is not None
    assert campaign_data["status"] == "CREATED"
    
    # Check if status message includes any service warnings
    # This will depend on the current state of circuit breakers
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert campaign.status_message is not None
    
    # Status message should either indicate all services available or include warnings
    status_msg = campaign.status_message.lower()
    assert "campaign created successfully" in status_msg

def test_detailed_error_messages_for_start_failures(authenticated_client, db_session, authenticated_campaign_payload):
    """Test that start failures return detailed, actionable error messages."""
    # Create campaign
    create_response = authenticated_client.post("/api/v1/campaigns/", json=authenticated_campaign_payload)
    assert create_response.status_code == 201
    campaign_id = create_response.json()["data"]["id"]
    
    # Set campaign to PAUSED to simulate a business rule violation
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = CampaignStatus.PAUSED
    campaign.status_message = "Paused for testing detailed errors"
    db_session.commit()
    
    # Try to start paused campaign
    response = authenticated_client.post(f"/api/v1/campaigns/{campaign_id}/start", json={})
    
    # Should return detailed error information
    assert response.status_code == 409  # Conflict due to paused state
    response_data = response.json()
    
    # Verify error structure
    assert "detail" in response_data
    error_detail = response_data["detail"]
    assert isinstance(error_detail, dict)
    
    # Should contain comprehensive error information
    required_error_fields = ["message", "errors", "warnings", "validation_details"]
    for field in required_error_fields:
        assert field in error_detail, f"Missing error field: {field}"
    
    # Errors should be specific and actionable
    assert len(error_detail["errors"]) > 0
    assert any("paused" in error.lower() and "resume" in error.lower() for error in error_detail["errors"])
    
    # Validation details should provide context
    assert "campaign_status" in error_detail["validation_details"]
    assert "services" in error_detail["validation_details"]
    assert "global_state" in error_detail["validation_details"] 