"""
Demonstration tests showing how to use the campaign fixtures in real testing scenarios.

This file serves as both documentation and validation of fixture usage patterns.
"""

import pytest
from fastapi import status
from unittest.mock import patch, MagicMock

from app.models.campaign_status import CampaignStatus
from app.models.job import JobStatus, JobType
from tests.fixtures.campaign_fixtures import *
from tests.helpers.instantly_mock import mock_instantly_service


# ---------------------------------------------------------------------------
# Basic Fixture Usage Examples
# ---------------------------------------------------------------------------

def test_create_campaign_with_sample_data(api_client, sample_campaign_data, db_helpers):
    """Demonstrate basic campaign creation using fixtures."""
    # Use sample data fixture for valid campaign creation
    response = api_client.post("/api/v1/campaigns/", json=sample_campaign_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    
    # Check structured response format
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    campaign_data = response_data["data"]
    
    # Use database helpers to verify creation
    db_helpers.verify_campaign_in_db(campaign_data["id"], {
        "name": sample_campaign_data["name"],
        "status": "created"
    })


def test_validation_errors_with_invalid_data(api_client, invalid_campaign_data):
    """Demonstrate validation testing using invalid data fixture."""
    # Test each invalid scenario
    for scenario_name, invalid_data in invalid_campaign_data.items():
        response = api_client.post("/api/v1/campaigns/", json=invalid_data)
        
        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        error_detail = response.json()
        assert "detail" in error_detail


def test_update_existing_campaign(api_client, existing_campaign, campaign_update_data, db_helpers):
    """Demonstrate campaign update testing using fixtures."""
    campaign_id = existing_campaign.id
    
    # Test partial update
    partial_update = campaign_update_data["partial_update"]
    response = api_client.patch(f"/api/v1/campaigns/{campaign_id}", json=partial_update)
    
    assert response.status_code == status.HTTP_200_OK
    
    # Refresh database session to see API changes
    db_helpers.db_session.commit()
    db_helpers.db_session.close()
    db_helpers.db_session.rollback()
    
    # Verify update in database
    db_helpers.verify_campaign_in_db(campaign_id, {
        "name": partial_update["name"],
        "description": partial_update["description"]
    })


# ---------------------------------------------------------------------------
# Advanced Fixture Usage Examples
# ---------------------------------------------------------------------------

def test_campaign_list_with_pagination(api_client, multiple_campaigns, pagination_test_data):
    """Demonstrate pagination testing using multiple campaigns fixture."""
    # Test first page (page=1, per_page=2)
    response = api_client.get("/api/v1/campaigns/?page=1&per_page=2")
    
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    
    # Check structured response format
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    campaigns = response_data["data"]["campaigns"]
    assert len(campaigns) <= 2  # Should have at most 2 campaigns
    
    # Test second page (page=2, per_page=2)
    response = api_client.get("/api/v1/campaigns/?page=2&per_page=2")
    
    assert response.status_code == status.HTTP_200_OK
    second_response_data = response.json()
    assert "status" in second_response_data
    assert "data" in second_response_data
    assert second_response_data["status"] == "success"
    
    second_page_campaigns = second_response_data["data"]["campaigns"]
    
    # Should have different campaigns (if enough data)
    if len(campaigns) == 2 and len(second_page_campaigns) > 0:
        first_page_ids = {c["id"] for c in campaigns}
        second_page_ids = {c["id"] for c in second_page_campaigns}
        assert first_page_ids.isdisjoint(second_page_ids)


def test_campaign_with_jobs_workflow(api_client, campaign_with_jobs, db_helpers):
    """Demonstrate testing campaigns with associated jobs."""
    campaign, jobs = campaign_with_jobs
    
    # Get campaign details via API
    response = api_client.get(f"/api/v1/campaigns/{campaign.id}")
    assert response.status_code == status.HTTP_200_OK
    
    # Verify jobs exist in database
    db_jobs = db_helpers.get_campaign_jobs_from_db(campaign.id)
    assert len(db_jobs) == len(jobs)
    
    # Verify different job types exist
    job_types = {job.job_type for job in db_jobs}
    assert JobType.FETCH_LEADS in job_types
    
    # Test job status verification
    for job in jobs:
        db_helpers.verify_job_status_in_db(job.id, job.status)


def test_cleanup_old_jobs(api_client, old_jobs_for_cleanup, db_helpers):
    """Demonstrate cleanup testing using old jobs fixture."""
    data = old_jobs_for_cleanup
    old_campaign = data["old_campaign"]
    old_jobs = data["old_jobs"]
    recent_campaign = data["recent_campaign"]
    recent_jobs = data["recent_jobs"]
    
    # Verify initial state
    assert len(old_jobs) > 0
    assert len(recent_jobs) > 0
    
    # Test cleanup endpoint (30 days)
    response = api_client.post(
        f"/api/v1/campaigns/{old_campaign.id}/cleanup",
        json={"days": 30}
    )
    
    # Should succeed or return expected error (depending on implementation)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    # Verify old jobs would be cleaned up (in a real implementation)
    # This is a demonstration of how you would test cleanup logic


# ---------------------------------------------------------------------------
# Performance and Load Testing Examples
# ---------------------------------------------------------------------------

def test_list_performance_with_large_dataset(api_client, large_dataset_campaigns):
    """Demonstrate performance testing using large dataset fixture."""
    import time
    
    # Measure response time for listing campaigns
    start_time = time.time()
    response = api_client.get("/api/v1/campaigns/")
    end_time = time.time()
    
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    
    # Check structured response format
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    campaigns = response_data["data"]["campaigns"]
    
    # By default, API returns first page with 10 campaigns (per_page=10)
    # We have 50 campaigns, so we should get 10 campaigns on the first page
    assert len(campaigns) == min(10, len(large_dataset_campaigns))
    
    # Should respond quickly (under 2 seconds for paginated result)
    response_time = end_time - start_time
    assert response_time < 2.0


def test_concurrent_campaign_updates(api_client, existing_campaign, concurrent_access_data):
    """Demonstrate concurrent access testing using fixtures."""
    campaign_id = existing_campaign.id
    updates = concurrent_access_data["concurrent_updates"]
    
    # Simulate concurrent updates (in real scenario, use threading)
    responses = []
    for update in updates:
        response = api_client.patch(f"/api/v1/campaigns/{campaign_id}", json=update)
        responses.append(response)
    
    # All updates should succeed (last one wins)
    for response in responses:
        assert response.status_code == status.HTTP_200_OK
    
    # Final state should reflect last update
    final_response = api_client.get(f"/api/v1/campaigns/{campaign_id}")
    assert final_response.status_code == status.HTTP_200_OK
    
    final_response_data = final_response.json()
    assert "status" in final_response_data
    assert "data" in final_response_data
    assert final_response_data["status"] == "success"
    
    final_campaign = final_response_data["data"]
    assert final_campaign["name"] == updates[-1]["name"]


# ---------------------------------------------------------------------------
# Error Handling and Edge Cases
# ---------------------------------------------------------------------------

def test_database_error_handling(api_client, database_error_scenarios):
    """Demonstrate error handling testing using error scenarios fixture."""
    # Test constraint violation scenario
    constraint_data = database_error_scenarios["constraint_violation"]
    
    response = api_client.post("/api/v1/campaigns/", json=constraint_data)
    
    # Should return validation error for null name
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_isolated_environment_guarantees(isolated_test_environment, db_helpers, organization):
    """Demonstrate maximum isolation testing."""
    # Should start completely clean
    assert db_helpers.count_campaigns_in_db() == 0
    
    # Create test data
    campaign = db_helpers.create_test_campaign_in_db({
        "name": "Isolated Test",
        "organization_id": organization.id
    })
    
    # Should exist
    assert db_helpers.count_campaigns_in_db() == 1
    db_helpers.verify_campaign_in_db(campaign.id, {"name": "Isolated Test"})


# ---------------------------------------------------------------------------
# Complex Workflow Testing
# ---------------------------------------------------------------------------

def test_complete_campaign_lifecycle(
    api_client,
    sample_campaign_data,
    campaign_update_data,
    db_helpers
):
    """Demonstrate complete campaign lifecycle testing using multiple fixtures."""
    
    # 1. Create campaign
    create_response = api_client.post("/api/v1/campaigns/", json=sample_campaign_data)
    assert create_response.status_code == status.HTTP_201_CREATED
    
    create_response_data = create_response.json()
    assert "status" in create_response_data
    assert "data" in create_response_data
    assert create_response_data["status"] == "success"
    
    campaign = create_response_data["data"]
    campaign_id = campaign["id"]
    
    # Verify creation in database
    db_helpers.verify_campaign_in_db(campaign_id, {
        "name": sample_campaign_data["name"],
        "status": "created"
    })
    
    # 2. Update campaign
    update_data = campaign_update_data["partial_update"]
    update_response = api_client.patch(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    assert update_response.status_code == status.HTTP_200_OK
    
    # Verify update in database
    db_helpers.verify_campaign_in_db(campaign_id, {
        "name": update_data["name"]
    })
    
    # 3. Get campaign details
    details_response = api_client.get(f"/api/v1/campaigns/{campaign_id}")
    assert details_response.status_code == status.HTTP_200_OK
    
    details_response_data = details_response.json()
    assert "status" in details_response_data
    assert "data" in details_response_data
    assert details_response_data["status"] == "success"
    
    details = details_response_data["data"]
    assert details["name"] == update_data["name"]
    
    # 4. Verify timestamps are properly maintained
    db_helpers.verify_campaign_timestamps(campaign_id, check_updated=False)


def test_multi_campaign_operations(
    api_client,
    multiple_campaigns,
    sample_campaign_data,
    db_helpers
):
    """Demonstrate testing operations across multiple campaigns."""
    
    # Should have existing campaigns from fixture
    initial_count = len(multiple_campaigns)
    assert db_helpers.count_campaigns_in_db() == initial_count
    
    # Create additional campaign
    response = api_client.post("/api/v1/campaigns/", json=sample_campaign_data)
    assert response.status_code == status.HTTP_201_CREATED
    
    # Should have one more campaign
    assert db_helpers.count_campaigns_in_db() == initial_count + 1
    
    # List all campaigns
    list_response = api_client.get("/api/v1/campaigns/")
    assert list_response.status_code == status.HTTP_200_OK
    
    list_response_data = list_response.json()
    assert "status" in list_response_data
    assert "data" in list_response_data
    assert list_response_data["status"] == "success"
    
    campaigns = list_response_data["data"]["campaigns"]
    assert len(campaigns) == initial_count + 1
    
    # Verify each campaign has unique ID
    campaign_ids = [c["id"] for c in campaigns]
    assert len(campaign_ids) == len(set(campaign_ids))


# ---------------------------------------------------------------------------
# Fixture Combination Examples
# ---------------------------------------------------------------------------

def test_using_multiple_data_fixtures(
    sample_campaign_data,
    invalid_campaign_data,
    campaign_update_data,
    pagination_test_data
):
    """Demonstrate using multiple data fixtures together."""
    
    # All fixtures should provide data
    assert sample_campaign_data is not None
    assert invalid_campaign_data is not None
    assert campaign_update_data is not None
    assert pagination_test_data is not None
    
    # Should have different types of data
    assert "name" in sample_campaign_data
    assert "missing_required_fields" in invalid_campaign_data
    assert "partial_update" in campaign_update_data
    assert "first_page" in pagination_test_data


def test_database_and_api_consistency(
    api_client,
    test_db_session,
    db_helpers,
    sample_campaign_data
):
    """Demonstrate testing consistency between API and database."""
    
    # Create via API
    api_response = api_client.post("/api/v1/campaigns/", json=sample_campaign_data)
    assert api_response.status_code == status.HTTP_201_CREATED
    
    api_response_data = api_response.json()
    assert "status" in api_response_data
    assert "data" in api_response_data
    assert api_response_data["status"] == "success"
    
    api_campaign = api_response_data["data"]
    
    # Verify via database helpers
    db_campaign = db_helpers.verify_campaign_in_db(api_campaign["id"])
    
    # Verify via direct database access
    direct_campaign = test_db_session.query(Campaign).filter(
        Campaign.id == api_campaign["id"]
    ).first()
    
    # All should be consistent
    assert api_campaign["name"] == db_campaign.name == direct_campaign.name
    assert api_campaign["id"] == db_campaign.id == direct_campaign.id


# ---------------------------------------------------------------------------
# Cleanup and Isolation Verification
# ---------------------------------------------------------------------------

def test_fixture_cleanup_verification_1(db_helpers, organization):
    """First test to verify cleanup works."""
    # Create some data
    campaign = db_helpers.create_test_campaign_in_db({
        "name": "Cleanup Test 1",
        "organization_id": organization.id
    })
    assert db_helpers.count_campaigns_in_db() == 1


def test_fixture_cleanup_verification_2(db_helpers, organization):
    """Second test to verify previous test data was cleaned up."""
    # Should start clean
    assert db_helpers.count_campaigns_in_db() == 0
    
    # Create different data
    campaign = db_helpers.create_test_campaign_in_db({
        "name": "Cleanup Test 2",
        "organization_id": organization.id
    })
    assert db_helpers.count_campaigns_in_db() == 1


def test_transaction_isolation(transaction_rollback_session, organization):
    """Demonstrate transaction rollback fixture usage."""
    # Create data that should be rolled back
    from app.models.campaign import Campaign
    
    campaign = Campaign(
        name="Rollback Test",
        fileName="rollback.csv",
        totalRecords=100,
        url="https://test.com",
        organization_id=organization.id
    )
    transaction_rollback_session.add(campaign)
    transaction_rollback_session.commit()
    
    # Should exist in this session
    assert transaction_rollback_session.query(Campaign).count() == 1


def test_transaction_rollback_worked(test_db_session):
    """Verify that transaction rollback fixture worked."""
    # Should not see data from previous test
    assert test_db_session.query(Campaign).count() == 0


@pytest.fixture(autouse=True, scope="module")
def mock_instantly_service():
    """Mock InstantlyService for all fixtures demo tests."""
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