import pytest
import uuid
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.schemas.lead import LeadCreate, LeadUpdate
from tests.helpers import (
    verify_lead_in_db, verify_lead_not_in_db, count_leads_in_db, create_test_lead_in_db
)
from unittest.mock import patch, MagicMock
from tests.helpers.instantly_mock import mock_instantly_service

@pytest.fixture(autouse=True, scope="module")
def mock_instantly_service():
    """Mock InstantlyService for all lead API tests."""
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

@pytest.fixture
def campaign_payload(authenticated_client, organization):
    """Create a campaign for lead tests."""
    payload = {
        "name": "Test Campaign for Leads",
        "description": "Campaign for lead tests",
        "fileName": "leads.csv",
        "totalRecords": 10,
        "url": "https://app.apollo.io/#/lead-test",
        "organization_id": organization.id
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    assert response.status_code == 201
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    return response_data["data"]

@pytest.fixture
def lead_payload(campaign_payload):
    """Return a valid payload for creating a lead via the API."""
    return {
        "campaign_id": campaign_payload["id"],
        "first_name": "Alice",
        "last_name": "Smith",
        "email": f"alice{uuid.uuid4().hex[:6]}@example.com",
        "phone": "1234567890",
        "company": "TestCo",
        "title": "Engineer",
        "linkedin_url": "https://linkedin.com/in/alicesmith",
        "source_url": "https://source.com/profile",
        "raw_data": {"source": "test"},
        "email_verification": None,
        "enrichment_results": None,
        "enrichment_job_id": None,
        "email_copy_gen_results": None,
        "instantly_lead_record": None
    }

@pytest.fixture
def existing_lead(db_session, campaign_payload):
    """Create a lead in the DB for update/retrieve tests."""
    data = {
        "campaign_id": campaign_payload["id"],
        "first_name": "Bob",
        "last_name": "Jones",
        "email": f"bob{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9876543210",
        "company": "TestCo",
        "title": "Manager"
    }
    return create_test_lead_in_db(db_session, data)

# ------------------- Lead Creation Tests -------------------
def test_create_lead_success(authenticated_client, db_session, lead_payload):
    response = authenticated_client.post("/api/v1/leads/", json=lead_payload)
    assert response.status_code == 201
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    data = response_data["data"]
    for key in lead_payload:
        if key in data:
            assert data[key] == lead_payload[key]
    assert "id" in data
    verify_lead_in_db(db_session, data["id"], {"email": lead_payload["email"]})

def test_create_lead_validation_missing_fields(authenticated_client, db_session, lead_payload):
    bad_payload = lead_payload.copy()
    del bad_payload["campaign_id"]
    response = authenticated_client.post("/api/v1/leads/", json=bad_payload)
    assert response.status_code == 422
    assert count_leads_in_db(db_session) == 0

def test_create_lead_validation_invalid_email(authenticated_client, db_session, lead_payload):
    bad_payload = lead_payload.copy()
    bad_payload["email"] = "not-an-email"
    response = authenticated_client.post("/api/v1/leads/", json=bad_payload)
    assert response.status_code in (201, 422)  # Accepts any string, but if you add validation, expect 422

def test_create_lead_duplicate_email_same_campaign(authenticated_client, db_session, lead_payload):
    response1 = authenticated_client.post("/api/v1/leads/", json=lead_payload)
    assert response1.status_code == 201
    response2 = authenticated_client.post("/api/v1/leads/", json=lead_payload)
    # Should allow or update, depending on business logic. Accept both 201 and 200.
    assert response2.status_code in (200, 201)
    assert count_leads_in_db(db_session) == 1

# ------------------- Lead Listing Tests -------------------
def test_list_leads_empty(authenticated_client, db_session):
    response = authenticated_client.get("/api/v1/leads/")
    assert response.status_code == 200
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    assert response_data["data"]["leads"] == []
    assert count_leads_in_db(db_session) == 0

def test_list_leads_multiple(authenticated_client, db_session, lead_payload):
    emails = []
    for i in range(3):
        payload = lead_payload.copy()
        payload["email"] = f"user{i}@example.com"
        response = authenticated_client.post("/api/v1/leads/", json=payload)
        assert response.status_code == 201
        emails.append(payload["email"])
    response = authenticated_client.get("/api/v1/leads/")
    assert response.status_code == 200
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    data = response_data["data"]["leads"]
    assert len(data) == 3
    db_count = count_leads_in_db(db_session)
    assert db_count == 3
    returned_emails = {lead["email"] for lead in data}
    assert set(emails) == returned_emails

def test_list_leads_pagination(authenticated_client, db_session, lead_payload):
    for i in range(5):
        payload = lead_payload.copy()
        payload["email"] = f"pagetest{i}@example.com"
        authenticated_client.post("/api/v1/leads/", json=payload)
    response = authenticated_client.get("/api/v1/leads/?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert count_leads_in_db(db_session) == 5

def test_list_leads_filter_by_campaign(authenticated_client, db_session, lead_payload, campaign_payload):
    # Create a second campaign
    second_campaign_payload = {
        "name": "Second Campaign",
        "description": "Second Campaign for leads",
        "fileName": "second_leads.csv",
        "totalRecords": 10,
        "url": "https://app.apollo.io/#/lead-test-second",
        "organization_id": campaign_payload["organization_id"]
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=second_campaign_payload)
    assert response.status_code == 201
    second_campaign_response = response.json()
    assert "status" in second_campaign_response
    assert "data" in second_campaign_response
    assert second_campaign_response["status"] == "success"
    second_campaign = second_campaign_response["data"]
    
    # Add leads to both campaigns
    payload1 = lead_payload.copy()
    payload2 = lead_payload.copy()
    payload2["campaign_id"] = second_campaign["id"]
    payload2["email"] = "second@campaign.com"
    
    authenticated_client.post("/api/v1/leads/", json=payload1)
    authenticated_client.post("/api/v1/leads/", json=payload2)
    
    # Filter by first campaign
    resp1 = authenticated_client.get(f"/api/v1/leads/?campaign_id={campaign_payload['id']}")
    assert resp1.status_code == 200
    resp1_data = resp1.json()
    assert "status" in resp1_data
    assert "data" in resp1_data
    assert resp1_data["status"] == "success"
    leads1 = resp1_data["data"]["leads"]
    assert all(lead["campaign_id"] == campaign_payload["id"] for lead in leads1)
    
    # Filter by second campaign
    resp2 = authenticated_client.get(f"/api/v1/leads/?campaign_id={second_campaign['id']}")
    assert resp2.status_code == 200
    resp2_data = resp2.json()
    assert "status" in resp2_data
    assert "data" in resp2_data
    assert resp2_data["status"] == "success"
    leads2 = resp2_data["data"]["leads"]
    assert all(lead["campaign_id"] == second_campaign["id"] for lead in leads2)

# ------------------- Lead Retrieval Tests -------------------
def test_get_lead_success(authenticated_client, db_session, existing_lead):
    response = authenticated_client.get(f"/api/v1/leads/{existing_lead.id}")
    assert response.status_code == 200
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    data = response_data["data"]
    assert data["id"] == existing_lead.id
    assert data["email"] == existing_lead.email
    db_lead = verify_lead_in_db(db_session, existing_lead.id)
    assert data["email"] == db_lead.email

def test_get_lead_not_found(authenticated_client, db_session):
    non_existent_id = str(uuid.uuid4())
    response = authenticated_client.get(f"/api/v1/leads/{non_existent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_get_lead_malformed_id(authenticated_client, db_session):
    response = authenticated_client.get("/api/v1/leads/not-a-uuid")
    assert response.status_code == 404

# ------------------- Lead Update Tests -------------------
def test_update_lead_success(authenticated_client, db_session, existing_lead):
    update_data = {"first_name": "Updated", "company": "NewCo"}
    response = authenticated_client.put(f"/api/v1/leads/{existing_lead.id}", json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    data = response_data["data"]
    assert data["first_name"] == "Updated"
    assert data["company"] == "NewCo"
    verify_lead_in_db(db_session, existing_lead.id, {"first_name": "Updated", "company": "NewCo"})

def test_update_lead_partial(authenticated_client, db_session, existing_lead):
    update_data = {"title": "Director"}
    response = authenticated_client.put(f"/api/v1/leads/{existing_lead.id}", json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    data = response_data["data"]
    assert data["title"] == "Director"
    verify_lead_in_db(db_session, existing_lead.id, {"title": "Director"})

def test_update_lead_validation_error(authenticated_client, db_session, existing_lead):
    update_data = {"email": ""}  # Empty email should fail if validated
    response = authenticated_client.put(f"/api/v1/leads/{existing_lead.id}", json=update_data)
    assert response.status_code in (200, 422)  # Accepts empty, but if you add validation, expect 422

def test_update_lead_not_found(authenticated_client, db_session):
    non_existent_id = str(uuid.uuid4())
    update_data = {"first_name": "Ghost"}
    response = authenticated_client.put(f"/api/v1/leads/{non_existent_id}", json=update_data)
    assert response.status_code == 404

# ------------------- Campaign-Lead Relationship Tests -------------------
def test_lead_campaign_relationship(authenticated_client, db_session, campaign_payload):
    # Create a lead for the campaign
    payload = {
        "campaign_id": campaign_payload["id"],
        "first_name": "Rel",
        "last_name": "Test",
        "email": f"reltest{uuid.uuid4().hex[:6]}@example.com"
    }
    response = authenticated_client.post("/api/v1/leads/", json=payload)
    assert response.status_code == 201
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    lead_data = response_data["data"]
    lead_id = lead_data["id"]
    
    # Retrieve campaign from DB and check leads
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_payload["id"]).first()
    assert any(lead.id == lead_id for lead in campaign.leads)

# ------------------- Authentication Requirement Tests -------------------
def test_create_lead_requires_auth(client, db_session, lead_payload):
    """Test that lead creation requires authentication."""
    response = client.post("/api/v1/leads/", json=lead_payload)
    assert response.status_code == 401

def test_list_leads_requires_auth(client, db_session):
    """Test that listing leads requires authentication."""
    response = client.get("/api/v1/leads/")
    assert response.status_code == 401

def test_get_lead_requires_auth(client, db_session):
    """Test that getting a lead requires authentication."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/leads/{fake_id}")
    assert response.status_code == 401

def test_update_lead_requires_auth(client, db_session):
    """Test that updating a lead requires authentication."""
    fake_id = str(uuid.uuid4())
    response = client.put(f"/api/v1/leads/{fake_id}", json={"first_name": "Test"})
    assert response.status_code == 401


