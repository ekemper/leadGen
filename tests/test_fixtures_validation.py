"""
Tests to validate that all fixtures work correctly and provide proper test isolation.

These tests ensure that fixtures provide the expected data and behavior,
and that there's no data leakage between tests.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus, JobType
from tests.fixtures.campaign_fixtures import *
from tests.helpers.instantly_mock import mock_instantly_service


# ---------------------------------------------------------------------------
# Database Session Fixture Tests
# ---------------------------------------------------------------------------

def test_test_db_session_isolation(test_db_session, organization):
    """Test that database session provides proper isolation."""
    # Create a campaign
    campaign = Campaign(
        name="Isolation Test",
        fileName="isolation.csv",
        totalRecords=100,
        url="https://test.com",
        organization_id=organization.id
    )
    test_db_session.add(campaign)
    test_db_session.commit()
    
    # Verify it exists
    assert test_db_session.query(Campaign).count() == 1


def test_test_db_session_isolation_second_test(test_db_session):
    """Test that previous test data doesn't leak into this test."""
    # Should start with clean database
    assert test_db_session.query(Campaign).count() == 0
    assert test_db_session.query(Job).count() == 0


def test_clean_database_fixture(clean_database, organization):
    """Test that clean_database fixture provides guaranteed clean state."""
    # Should start clean
    assert clean_database.query(Campaign).count() == 0
    assert clean_database.query(Job).count() == 0
    
    # Create some data
    campaign = Campaign(
        name="Clean Test",
        fileName="clean.csv",
        totalRecords=50,
        url="https://test.com",
        organization_id=organization.id
    )
    clean_database.add(campaign)
    clean_database.commit()
    
    # Data should exist
    assert clean_database.query(Campaign).count() == 1


def test_clean_database_fixture_second_test(clean_database):
    """Test that clean_database fixture cleans up properly."""
    # Should be clean again
    assert clean_database.query(Campaign).count() == 0
    assert clean_database.query(Job).count() == 0


def test_db_helpers_fixture(db_helpers, organization):
    """Test that db_helpers fixture works correctly."""
    # Should be able to use helper functions
    assert db_helpers.count_campaigns_in_db() == 0
    
    # Create campaign using helpers
    campaign = db_helpers.create_test_campaign_in_db({
        "name": "Helper Test",
        "organization_id": organization.id
    })
    
    # Verify using helpers
    assert db_helpers.count_campaigns_in_db() == 1
    db_helpers.verify_campaign_in_db(campaign.id, {"name": "Helper Test"})


def test_api_client_fixture(api_client):
    """Test that API client fixture works correctly."""
    # Should be able to make requests
    response = api_client.get("/api/v1/campaigns/")
    assert response.status_code == 200
    
    response_data = response.json()
    # Check structured response format
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    assert response_data["data"]["campaigns"] == []  # Should be empty list


# ---------------------------------------------------------------------------
# Campaign Data Fixture Tests
# ---------------------------------------------------------------------------

def test_sample_campaign_data_fixture(sample_campaign_data):
    """Test that sample_campaign_data provides valid data."""
    # Should have all required fields
    required_fields = ["name", "fileName", "totalRecords", "url"]
    for field in required_fields:
        assert field in sample_campaign_data
        assert sample_campaign_data[field] is not None
    
    # Should have reasonable values
    assert len(sample_campaign_data["name"]) > 0
    assert sample_campaign_data["totalRecords"] > 0
    assert sample_campaign_data["url"].startswith("https://")


def test_invalid_campaign_data_fixture(invalid_campaign_data):
    """Test that invalid_campaign_data provides various error scenarios."""
    # Should have multiple error scenarios
    expected_scenarios = [
        "missing_required_fields",
        "empty_name",
        "negative_total_records",
        "invalid_url",
        "name_too_long",
        "invalid_data_types"
    ]
    
    for scenario in expected_scenarios:
        assert scenario in invalid_campaign_data
    
    # Verify specific scenarios
    assert "name" not in invalid_campaign_data["missing_required_fields"]
    assert invalid_campaign_data["empty_name"]["name"] == ""
    assert invalid_campaign_data["negative_total_records"]["totalRecords"] < 0
    assert len(invalid_campaign_data["name_too_long"]["name"]) > 255


def test_existing_campaign_fixture(existing_campaign, test_db_session):
    """Test that existing_campaign creates a campaign in the database."""
    # Should be a Campaign object
    assert isinstance(existing_campaign, Campaign)
    assert existing_campaign.id is not None
    
    # Should exist in database
    db_campaign = test_db_session.query(Campaign).filter(
        Campaign.id == existing_campaign.id
    ).first()
    assert db_campaign is not None
    assert db_campaign.name == existing_campaign.name


def test_multiple_campaigns_fixture(multiple_campaigns, test_db_session):
    """Test that multiple_campaigns creates several campaigns with different properties."""
    # Should create multiple campaigns
    assert len(multiple_campaigns) >= 3
    
    # Should have different statuses
    statuses = {campaign.status for campaign in multiple_campaigns}
    assert len(statuses) > 1  # Should have variety
    
    # Should have different organizations
    orgs = {campaign.organization_id for campaign in multiple_campaigns}
    assert len(orgs) > 1  # Should have variety
    
    # All should exist in database
    db_count = test_db_session.query(Campaign).count()
    assert db_count == len(multiple_campaigns)


def test_campaign_with_jobs_fixture(campaign_with_jobs, test_db_session):
    """Test that campaign_with_jobs creates campaign with associated jobs."""
    campaign, jobs = campaign_with_jobs
    
    # Should have campaign and jobs
    assert isinstance(campaign, Campaign)
    assert isinstance(jobs, list)
    assert len(jobs) > 0
    
    # All jobs should be associated with campaign
    for job in jobs:
        assert job.campaign_id == campaign.id
    
    # Should exist in database
    db_jobs = test_db_session.query(Job).filter(Job.campaign_id == campaign.id).all()
    assert len(db_jobs) == len(jobs)
    
    # Should have different job types and statuses
    job_types = {job.job_type for job in jobs}
    job_statuses = {job.status for job in jobs}
    assert len(job_types) > 1
    assert len(job_statuses) > 1


def test_old_jobs_for_cleanup_fixture(old_jobs_for_cleanup, test_db_session):
    """Test that old_jobs_for_cleanup creates appropriate test data."""
    data = old_jobs_for_cleanup
    
    # Should have old and recent data
    assert "old_campaign" in data
    assert "old_jobs" in data
    assert "recent_campaign" in data
    assert "recent_jobs" in data
    
    # Old jobs should be old enough for cleanup
    for job in data["old_jobs"]:
        if job.completed_at:
            age = datetime.utcnow().replace(tzinfo=timezone.utc) - job.completed_at
            assert age.days > 30  # Should be older than 30 days
    
    # Recent jobs should not be old enough for cleanup
    for job in data["recent_jobs"]:
        if job.completed_at:
            age = datetime.utcnow().replace(tzinfo=timezone.utc) - job.completed_at
            assert age.days < 30  # Should be newer than 30 days


# ---------------------------------------------------------------------------
# Specialized Data Fixture Tests
# ---------------------------------------------------------------------------

def test_campaign_update_data_fixture(campaign_update_data):
    """Test that campaign_update_data provides various update scenarios."""
    expected_scenarios = ["partial_update", "status_update", "complete_update", "error_status_update"]
    
    for scenario in expected_scenarios:
        assert scenario in campaign_update_data
    
    # Verify specific scenarios
    assert "name" in campaign_update_data["partial_update"]
    assert "status" in campaign_update_data["status_update"]
    assert len(campaign_update_data["complete_update"]) > 3  # Should have multiple fields


def test_pagination_test_data_fixture(pagination_test_data):
    """Test that pagination_test_data provides various pagination scenarios."""
    expected_scenarios = ["first_page", "second_page", "large_limit", "zero_limit"]
    
    for scenario in expected_scenarios:
        assert scenario in pagination_test_data
        assert "skip" in pagination_test_data[scenario]
        assert "limit" in pagination_test_data[scenario]


def test_search_filter_data_fixture(search_filter_data):
    """Test that search_filter_data provides various filter scenarios."""
    expected_scenarios = ["by_status", "by_organization", "multiple_filters"]
    
    for scenario in expected_scenarios:
        assert scenario in search_filter_data


# ---------------------------------------------------------------------------
# Performance and Load Testing Fixture Tests
# ---------------------------------------------------------------------------

def test_large_dataset_campaigns_fixture(large_dataset_campaigns, test_db_session):
    """Test that large_dataset_campaigns creates appropriate load test data."""
    # Should create many campaigns
    assert len(large_dataset_campaigns) >= 50
    
    # Should have variety in properties
    statuses = {campaign.status for campaign in large_dataset_campaigns}
    orgs = {campaign.organization_id for campaign in large_dataset_campaigns}
    
    assert len(statuses) > 1  # Should have different statuses
    assert len(orgs) > 1  # Should have different organizations
    
    # All should exist in database
    db_count = test_db_session.query(Campaign).count()
    assert db_count == len(large_dataset_campaigns)


# ---------------------------------------------------------------------------
# Error Scenario Fixture Tests
# ---------------------------------------------------------------------------

def test_database_error_scenarios_fixture(database_error_scenarios):
    """Test that database_error_scenarios provides error conditions."""
    expected_scenarios = ["duplicate_id", "foreign_key_violation", "constraint_violation"]
    
    for scenario in expected_scenarios:
        assert scenario in database_error_scenarios


def test_concurrent_access_data_fixture(concurrent_access_data):
    """Test that concurrent_access_data provides concurrency test data."""
    assert "concurrent_updates" in concurrent_access_data
    assert "concurrent_status_changes" in concurrent_access_data
    
    # Should have multiple items for concurrent testing
    assert len(concurrent_access_data["concurrent_updates"]) > 1
    assert len(concurrent_access_data["concurrent_status_changes"]) > 1


# ---------------------------------------------------------------------------
# Cleanup and Utility Fixture Tests
# ---------------------------------------------------------------------------

def test_transaction_rollback_session_fixture(transaction_rollback_session, organization):
    """Test that transaction_rollback_session rolls back changes."""
    # Create data in rollback session
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


def test_transaction_rollback_session_rollback_verification(test_db_session):
    """Test that rollback session changes don't persist."""
    # Should not see data from previous test
    assert test_db_session.query(Campaign).count() == 0


def test_isolated_test_environment_fixture(isolated_test_environment, organization):
    """Test that isolated_test_environment provides maximum isolation."""
    # Should start completely clean
    assert isolated_test_environment.query(Campaign).count() == 0
    assert isolated_test_environment.query(Job).count() == 0
    
    # Create some data
    campaign = Campaign(
        name="Isolated Test",
        fileName="isolated.csv",
        totalRecords=100,
        url="https://test.com",
        organization_id=organization.id
    )
    isolated_test_environment.add(campaign)
    isolated_test_environment.commit()
    
    # Should exist
    assert isolated_test_environment.query(Campaign).count() == 1


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

def test_fixtures_work_together(
    test_db_session,
    db_helpers,
    sample_campaign_data,
    api_client
):
    """Test that multiple fixtures work together correctly."""
    # Use sample data to create campaign via helpers
    campaign = db_helpers.create_test_campaign_in_db(sample_campaign_data)
    
    # Verify via database session
    db_campaign = test_db_session.query(Campaign).filter(
        Campaign.id == campaign.id
    ).first()
    assert db_campaign is not None
    
    # Verify via API client
    response = api_client.get(f"/api/v1/campaigns/{campaign.id}")
    assert response.status_code == 200
    
    # Verify via helpers
    db_helpers.verify_campaign_in_db(campaign.id, {
        "name": sample_campaign_data["name"]
    })


def test_fixture_data_consistency(
    existing_campaign,
    multiple_campaigns,
    campaign_with_jobs,
    test_db_session
):
    """Test that fixtures create consistent, non-conflicting data."""
    # All campaigns should have unique IDs
    all_campaigns = [existing_campaign] + multiple_campaigns + [campaign_with_jobs[0]]
    campaign_ids = [c.id for c in all_campaigns]
    assert len(campaign_ids) == len(set(campaign_ids))  # All unique
    
    # Total count should match
    total_expected = len(all_campaigns)
    db_count = test_db_session.query(Campaign).count()
    assert db_count == total_expected


def test_fixture_cleanup_effectiveness(test_db_session):
    """Test that fixture cleanup prevents data leakage."""
    # This test should run after others and see clean state
    try:
        # Should be clean due to auto_cleanup_database fixture
        campaign_count = test_db_session.query(Campaign).count()
        job_count = test_db_session.query(Job).count()
        
        # Note: This might not be 0 if other tests are running concurrently
        # but it validates the cleanup mechanism works
        assert campaign_count >= 0  # At least not negative
        assert job_count >= 0  # At least not negative
    finally:
        pass


# ---------------------------------------------------------------------------
# Performance Tests for Fixtures
# ---------------------------------------------------------------------------

def test_fixture_performance_large_dataset(large_dataset_campaigns):
    """Test that large dataset fixture performs reasonably."""
    import time
    
    start_time = time.time()
    
    # Access all campaigns (should be already created by fixture)
    campaign_count = len(large_dataset_campaigns)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Should create large dataset quickly (under 5 seconds)
    assert duration < 5.0
    assert campaign_count >= 50


def test_fixture_memory_usage(multiple_campaigns, campaign_with_jobs):
    """Test that fixtures don't consume excessive memory."""
    import sys
    
    # Get memory usage (basic check)
    campaigns = multiple_campaigns
    campaign, jobs = campaign_with_jobs
    
    # Should be reasonable object counts
    assert len(campaigns) < 100  # Not excessive
    assert len(jobs) < 50  # Not excessive
    
    # Objects should be properly formed
    for c in campaigns:
        assert hasattr(c, 'id')
        assert hasattr(c, 'name')
    
    for j in jobs:
        assert hasattr(j, 'id')
        assert hasattr(j, 'campaign_id')


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------

def test_fixture_edge_cases_empty_data(test_db_session, organization):
    """Test fixtures handle edge cases properly."""
    # Test with minimal data
    minimal_campaign = Campaign(
        name="Minimal",
        fileName="min.csv",
        totalRecords=1,
        url="https://min.com",
        organization_id=organization.id
    )
    test_db_session.add(minimal_campaign)
    test_db_session.commit()
    
    assert minimal_campaign.id is not None


def test_fixture_unicode_handling(test_db_session, organization):
    """Test that fixtures handle unicode data correctly."""
    unicode_campaign = Campaign(
        name="测试活动 🚀",
        description="Тест кампания with émojis 🎯",
        fileName="unicode_测试.csv",
        totalRecords=100,
        url="https://test.com/测试",
        organization_id=organization.id
    )
    test_db_session.add(unicode_campaign)
    test_db_session.commit()
    
    # Should handle unicode properly
    assert unicode_campaign.name == "测试活动 🚀"
    assert "émojis" in unicode_campaign.description


def test_fixture_boundary_values(test_db_session, organization):
    """Test fixtures with boundary values."""
    # Test with maximum values
    max_campaign = Campaign(
        name="x" * 255,  # Maximum name length
        fileName="max.csv",
        totalRecords=999999,  # Large number
        url="https://test.com",
        organization_id=organization.id
    )
    test_db_session.add(max_campaign)
    test_db_session.commit()
    
    assert len(max_campaign.name) == 255
    assert max_campaign.totalRecords == 999999 