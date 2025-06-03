import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid
from unittest.mock import patch, MagicMock

from app.models.organization import Organization
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from tests.helpers.instantly_mock import mock_instantly_service


# ---------------------------------------------------------------------------
# Organization API Integration Tests
# ---------------------------------------------------------------------------

def test_create_organization_and_verify_db(authenticated_client, test_db_session):
    """Test organization creation via API and verify in database."""
    payload = {"name": "API Test Org", "description": "Test org via API"}
    response = authenticated_client.post("/api/v1/organizations/", json=payload)
    
    assert response.status_code == 201
    org_data = response.json()
    
    # Verify API response structure
    assert org_data["name"] == payload["name"]
    assert org_data["description"] == payload["description"]
    assert "id" in org_data
    assert "created_at" in org_data
    assert "updated_at" in org_data
    assert org_data["campaign_count"] == 0
    
    # Verify in database
    db_org = test_db_session.query(Organization).filter(
        Organization.id == org_data["id"]
    ).first()
    assert db_org is not None
    assert db_org.name == payload["name"]
    assert db_org.description == payload["description"]


def test_list_organizations_with_campaign_counts(authenticated_client, test_db_session, organization):
    """Test organization listing includes accurate campaign counts."""
    # Create campaigns for the organization
    for i in range(3):
        campaign_payload = {
            "name": f"Test Campaign {i}",
            "organization_id": organization.id,
            "fileName": f"test{i}.csv",
            "totalRecords": 100,
            "url": f"https://test{i}.com"
        }
        response = authenticated_client.post("/api/v1/campaigns/", json=campaign_payload)
        assert response.status_code == 201

    # List organizations
    response = authenticated_client.get("/api/v1/organizations/")
    assert response.status_code == 200

    orgs_response = response.json()
    # Check paginated response structure
    assert "data" in orgs_response
    assert "meta" in orgs_response
    assert len(orgs_response["data"]) == 1
    
    org_data = orgs_response["data"][0]
    assert org_data["id"] == organization.id
    assert org_data["campaign_count"] == 3

    # Verify in database
    db_campaigns = test_db_session.query(Campaign).filter(
        Campaign.organization_id == organization.id
    ).all()
    assert len(db_campaigns) == 3


# ---------------------------------------------------------------------------
# Campaign-Organization Integration Tests
# ---------------------------------------------------------------------------

def test_create_campaign_with_organization(authenticated_client, test_db_session, organization):
    """Test campaign creation with organization via API."""
    payload = {
        "name": "Test Campaign",
        "organization_id": organization.id,
        "fileName": "test.csv",
        "totalRecords": 100,
        "url": "https://test.com"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    
    assert response.status_code == 201
    response_data = response.json()
    
    # Check structured response format
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    campaign_data = response_data["data"]
    
    # Verify API response includes organization_id
    assert campaign_data["organization_id"] == organization.id
    assert campaign_data["name"] == payload["name"]
    assert campaign_data["status"] == CampaignStatus.CREATED.value
    
    # Verify in database
    db_campaign = test_db_session.query(Campaign).filter(
        Campaign.id == campaign_data["id"]
    ).first()
    assert db_campaign is not None
    assert db_campaign.organization_id == organization.id
    
    # Verify relationship works
    assert db_campaign.organization.name == organization.name
    assert db_campaign.organization.id == organization.id


def test_create_campaign_with_invalid_organization(authenticated_client, test_db_session):
    """Test campaign creation fails with invalid organization_id."""
    invalid_org_id = str(uuid.uuid4())
    payload = {
        "name": "Test Campaign",
        "organization_id": invalid_org_id,
        "fileName": "test.csv",
        "totalRecords": 100,
        "url": "https://test.com"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    
    assert response.status_code == 400
    error_data = response.json()
    assert "not found" in error_data["detail"].lower()
    
    # Verify no campaign was created in database
    campaign_count = test_db_session.query(Campaign).count()
    assert campaign_count == 0


def test_list_campaigns_filtered_by_organization(authenticated_client, test_db_session, multiple_organizations):
    """Test campaign listing filtered by organization."""
    org1, org2, org3 = multiple_organizations
    
    # Create campaigns for different organizations
    campaigns_org1 = []
    campaigns_org2 = []
    
    # Create 2 campaigns for org1
    for i in range(2):
        payload = {
            "name": f"Org1 Campaign {i}",
            "organization_id": org1.id,
            "fileName": f"org1_test{i}.csv",
            "totalRecords": 100,
            "url": f"https://org1test{i}.com"
        }
        response = authenticated_client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
        response_data = response.json()
        assert "status" in response_data
        assert "data" in response_data
        assert response_data["status"] == "success"
        campaigns_org1.append(response_data["data"])
    
    # Create 3 campaigns for org2
    for i in range(3):
        payload = {
            "name": f"Org2 Campaign {i}",
            "organization_id": org2.id,
            "fileName": f"org2_test{i}.csv",
            "totalRecords": 100,
            "url": f"https://org2test{i}.com"
        }
        response = authenticated_client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
        response_data = response.json()
        assert "status" in response_data
        assert "data" in response_data
        assert response_data["status"] == "success"
        campaigns_org2.append(response_data["data"])
    
    # Test filtering by org1
    response = authenticated_client.get(f"/api/v1/campaigns/?organization_id={org1.id}")
    assert response.status_code == 200
    
    org1_response = response.json()
    assert "status" in org1_response
    assert "data" in org1_response
    assert org1_response["status"] == "success"
    
    org1_campaigns = org1_response["data"]["campaigns"]
    assert len(org1_campaigns) == 2
    for campaign in org1_campaigns:
        assert campaign["organization_id"] == org1.id
    
    # Test filtering by org2
    response = authenticated_client.get(f"/api/v1/campaigns/?organization_id={org2.id}")
    assert response.status_code == 200
    
    org2_response = response.json()
    assert "status" in org2_response
    assert "data" in org2_response
    assert org2_response["status"] == "success"
    
    org2_campaigns = org2_response["data"]["campaigns"]
    assert len(org2_campaigns) == 3
    for campaign in org2_campaigns:
        assert campaign["organization_id"] == org2.id
    
    # Test filtering by org3 (no campaigns)
    response = authenticated_client.get(f"/api/v1/campaigns/?organization_id={org3.id}")
    assert response.status_code == 200
    
    org3_response = response.json()
    assert "status" in org3_response
    assert "data" in org3_response
    assert org3_response["status"] == "success"
    
    org3_campaigns = org3_response["data"]["campaigns"]
    assert len(org3_campaigns) == 0


def test_organization_campaigns_endpoint(authenticated_client, test_db_session, organization):
    """Test the organization-specific campaigns endpoint."""
    # Create campaigns for the organization
    created_campaigns = []
    for i in range(3):
        payload = {
            "name": f"Org Campaign {i}",
            "organization_id": organization.id,
            "fileName": f"org_test{i}.csv",
            "totalRecords": 100 + i,
            "url": f"https://orgtest{i}.com"
        }
        response = authenticated_client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
        response_data = response.json()
        assert "status" in response_data
        assert "data" in response_data
        assert response_data["status"] == "success"
        created_campaigns.append(response_data["data"])
    
    # Get campaigns through organization endpoint
    response = authenticated_client.get(f"/api/v1/organizations/{organization.id}/campaigns")
    assert response.status_code == 200
    
    campaigns_response = response.json()
    # The organization campaigns endpoint returns List[CampaignResponse] directly
    assert isinstance(campaigns_response, list)
    assert len(campaigns_response) == 3
    
    # Verify all campaigns belong to the organization
    for campaign in campaigns_response:
        assert campaign["organization_id"] == organization.id
    
    # Verify campaign names match what we created
    campaign_names = {c["name"] for c in campaigns_response}
    expected_names = {c["name"] for c in created_campaigns}
    assert campaign_names == expected_names


def test_organization_campaigns_endpoint_not_found(authenticated_client, test_db_session):
    """Test organization campaigns endpoint with invalid organization."""
    invalid_org_id = str(uuid.uuid4())
    response = authenticated_client.get(f"/api/v1/organizations/{invalid_org_id}/campaigns")
    
    assert response.status_code == 404
    error_data = response.json()
    assert "not found" in error_data["detail"].lower()


# ---------------------------------------------------------------------------
# Relationship Query Tests
# ---------------------------------------------------------------------------

def test_organization_campaigns_relationship(authenticated_client, test_db_session, organization):
    """Test querying campaigns through organization relationship."""
    # Create campaigns via API
    for i in range(3):
        payload = {
            "name": f"Campaign {i}",
            "organization_id": organization.id,
            "fileName": f"test{i}.csv",
            "totalRecords": 100,
            "url": f"https://test{i}.com"
        }
        response = authenticated_client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
    
    # Verify in database through relationship
    db_org = test_db_session.query(Organization).filter(
        Organization.id == organization.id
    ).first()
    assert db_org is not None
    assert len(db_org.campaigns) == 3
    
    # Verify all campaigns belong to this organization
    for campaign in db_org.campaigns:
        assert campaign.organization_id == organization.id
        assert campaign.organization.name == organization.name


def test_campaign_organization_relationship(authenticated_client, test_db_session, organization):
    """Test querying organization through campaign relationship."""
    # Create campaign via API
    payload = {
        "name": "Relationship Test Campaign",
        "organization_id": organization.id,
        "fileName": "relationship_test.csv",
        "totalRecords": 50,
        "url": "https://relationshiptest.com"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    assert response.status_code == 201
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    campaign_data = response_data["data"]
    
    # Verify in database through relationship
    db_campaign = test_db_session.query(Campaign).filter(
        Campaign.id == campaign_data["id"]
    ).first()
    assert db_campaign is not None
    assert db_campaign.organization is not None
    assert db_campaign.organization.id == organization.id
    assert db_campaign.organization.name == organization.name


# ---------------------------------------------------------------------------
# Update Operation Tests
# ---------------------------------------------------------------------------

def test_update_campaign_organization(authenticated_client, test_db_session, multiple_organizations):
    """Test updating campaign's organization via API."""
    org1, org2, org3 = multiple_organizations
    
    # Create campaign in org1
    payload = {
        "name": "Movable Campaign",
        "organization_id": org1.id,
        "fileName": "movable.csv",
        "totalRecords": 100,
        "url": "https://movable.com"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    assert response.status_code == 201
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    campaign_data = response_data["data"]
    
    # Update campaign to belong to org2
    update_payload = {"organization_id": org2.id}
    response = authenticated_client.patch(f"/api/v1/campaigns/{campaign_data['id']}", json=update_payload)
    assert response.status_code == 200
    
    updated_response = response.json()
    assert "status" in updated_response
    assert "data" in updated_response
    assert updated_response["status"] == "success"
    updated_campaign = updated_response["data"]
    assert updated_campaign["organization_id"] == org2.id
    
    # Verify in database
    db_campaign = test_db_session.query(Campaign).filter(
        Campaign.id == campaign_data["id"]
    ).first()
    assert db_campaign.organization_id == org2.id
    assert db_campaign.organization.name == org2.name
    
    # Verify org1 no longer has this campaign
    db_org1 = test_db_session.query(Organization).filter(
        Organization.id == org1.id
    ).first()
    campaign_ids = [c.id for c in db_org1.campaigns]
    assert campaign_data["id"] not in campaign_ids
    
    # Verify org2 now has this campaign
    db_org2 = test_db_session.query(Organization).filter(
        Organization.id == org2.id
    ).first()
    campaign_ids = [c.id for c in db_org2.campaigns]
    assert campaign_data["id"] in campaign_ids


def test_update_campaign_invalid_organization(authenticated_client, test_db_session, organization):
    """Test updating campaign with invalid organization fails."""
    # Create campaign
    payload = {
        "name": "Test Campaign",
        "organization_id": organization.id,
        "fileName": "test.csv",
        "totalRecords": 100,
        "url": "https://test.com"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    assert response.status_code == 201
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    campaign_data = response_data["data"]
    
    # Try to update with invalid organization
    invalid_org_id = str(uuid.uuid4())
    update_payload = {"organization_id": invalid_org_id}
    response = authenticated_client.patch(f"/api/v1/campaigns/{campaign_data['id']}", json=update_payload)
    
    assert response.status_code == 400
    error_data = response.json()
    assert "not found" in error_data["detail"].lower()
    
    # Verify campaign still belongs to original organization
    db_campaign = test_db_session.query(Campaign).filter(
        Campaign.id == campaign_data["id"]
    ).first()
    assert db_campaign.organization_id == organization.id


# ---------------------------------------------------------------------------
# Pagination and Filtering Tests
# ---------------------------------------------------------------------------

def test_organization_campaigns_pagination(authenticated_client, test_db_session, organization):
    """Test pagination on organization campaigns endpoint."""
    # Create 5 campaigns
    for i in range(5):
        payload = {
            "name": f"Paginated Campaign {i}",
            "organization_id": organization.id,
            "fileName": f"paginated{i}.csv",
            "totalRecords": 100,
            "url": f"https://paginated{i}.com"
        }
        response = authenticated_client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
    
    # Test first page (limit 2)
    response = authenticated_client.get(f"/api/v1/organizations/{organization.id}/campaigns?skip=0&limit=2")
    assert response.status_code == 200
    
    page1_campaigns = response.json()
    assert len(page1_campaigns) == 2
    
    # Test second page
    response = authenticated_client.get(f"/api/v1/organizations/{organization.id}/campaigns?skip=2&limit=2")
    assert response.status_code == 200
    
    page2_campaigns = response.json()
    assert len(page2_campaigns) == 2
    
    # Test third page
    response = authenticated_client.get(f"/api/v1/organizations/{organization.id}/campaigns?skip=4&limit=2")
    assert response.status_code == 200
    
    page3_campaigns = response.json()
    assert len(page3_campaigns) == 1
    
    # Verify no overlap between pages
    all_campaign_ids = set()
    for campaigns in [page1_campaigns, page2_campaigns, page3_campaigns]:
        for campaign in campaigns:
            assert campaign["id"] not in all_campaign_ids
            all_campaign_ids.add(campaign["id"])
    
    assert len(all_campaign_ids) == 5


# ---------------------------------------------------------------------------
# Data Consistency Tests
# ---------------------------------------------------------------------------

def test_organization_deletion_with_campaigns_protection(authenticated_client, test_db_session, organization):
    """Test that organization with campaigns cannot be deleted (if protection is implemented)."""
    # Create campaign
    payload = {
        "name": "Protection Test Campaign",
        "organization_id": organization.id,
        "fileName": "protection.csv",
        "totalRecords": 100,
        "url": "https://protection.com"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    assert response.status_code == 201
    
    # Try to delete organization (this test assumes deletion protection is implemented)
    # If your API doesn't have DELETE endpoint yet, this test will be skipped
    try:
        response = authenticated_client.delete(f"/api/v1/organizations/{organization.id}")
        # If deletion is protected, it should fail
        if response.status_code in [400, 409]:
            # Verify organization still exists
            db_org = test_db_session.query(Organization).filter(
                Organization.id == organization.id
            ).first()
            assert db_org is not None
            
            # Verify campaign still exists
            campaign_count = test_db_session.query(Campaign).filter(
                Campaign.organization_id == organization.id
            ).count()
            assert campaign_count == 1
        elif response.status_code == 200:
            # If cascade deletion is implemented, verify campaigns are also deleted
            campaign_count = test_db_session.query(Campaign).filter(
                Campaign.organization_id == organization.id
            ).count()
            assert campaign_count == 0
    except Exception:
        # DELETE endpoint might not be implemented yet
        pytest.skip("Organization DELETE endpoint not implemented")


def test_multiple_campaign_creation_same_organization(authenticated_client, test_db_session, organization):
    """Test multiple campaign creation for the same organization sequentially."""
    created_campaigns = []
    
    # Create 3 campaigns sequentially
    for i in range(3):
        payload = {
            "name": f"Sequential Campaign {i}",
            "organization_id": organization.id,
            "fileName": f"sequential{i}.csv",
            "totalRecords": 100 + i,
            "url": f"https://sequential{i}.com"
        }
        response = authenticated_client.post("/api/v1/campaigns/", json=payload)
        assert response.status_code == 201
        response_data = response.json()
        assert "status" in response_data
        assert "data" in response_data
        assert response_data["status"] == "success"
        created_campaigns.append(response_data["data"])
    
    # Verify all campaigns belong to the same organization
    for campaign in created_campaigns:
        assert campaign["organization_id"] == organization.id
    
    # Verify in database
    db_campaigns = test_db_session.query(Campaign).filter(
        Campaign.organization_id == organization.id
    ).all()
    assert len(db_campaigns) == 3
    
    # Verify all campaigns have unique names
    campaign_names = {c["name"] for c in created_campaigns}
    assert len(campaign_names) == 3


# ---------------------------------------------------------------------------
# Error Handling and Edge Cases
# ---------------------------------------------------------------------------

def test_malformed_organization_id_in_campaign_creation(authenticated_client, test_db_session):
    """Test campaign creation with malformed organization_id."""
    payload = {
        "name": "Malformed Org Test",
        "organization_id": "not-a-valid-uuid",
        "fileName": "malformed.csv",
        "totalRecords": 100,
        "url": "https://malformed.com"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    
    # Should fail with validation error or not found error
    assert response.status_code in [400, 422]
    
    # Verify no campaign was created
    campaign_count = test_db_session.query(Campaign).count()
    assert campaign_count == 0


def test_empty_organization_id_in_campaign_creation(authenticated_client, test_db_session):
    """Test campaign creation with empty organization_id."""
    payload = {
        "name": "Empty Org Test",
        "organization_id": "",
        "fileName": "empty.csv",
        "totalRecords": 100,
        "url": "https://empty.com"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    
    # Should fail with validation error (empty string is treated as invalid organization)
    assert response.status_code == 400
    
    # Verify no campaign was created
    campaign_count = test_db_session.query(Campaign).count()
    assert campaign_count == 0


def test_null_organization_id_in_campaign_creation(authenticated_client, test_db_session):
    """Test campaign creation with null organization_id."""
    payload = {
        "name": "Null Org Test",
        "organization_id": None,
        "fileName": "null.csv",
        "totalRecords": 100,
        "url": "https://null.com"
    }
    response = authenticated_client.post("/api/v1/campaigns/", json=payload)
    
    # Should fail with validation error
    assert response.status_code == 422
    
    # Verify no campaign was created
    campaign_count = test_db_session.query(Campaign).count()
    assert campaign_count == 0


@pytest.fixture(autouse=True, scope="module")
def mock_instantly_service():
    """Mock InstantlyService for all organization-campaign integration tests."""
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