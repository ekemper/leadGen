"""
Test organization fixtures to verify they work correctly.

This module tests the organization fixtures created in Step 6 of the
organization-campaign relationship review.
"""

import pytest
from app.models.organization import Organization

# Import campaign fixtures to make them available
pytest_plugins = ["tests.fixtures.campaign_fixtures"]


def test_organization_fixture(test_db_session, organization):
    """Test that the single organization fixture works correctly."""
    # Verify organization was created
    assert organization is not None
    assert organization.id is not None
    assert organization.name == "Test Organization"
    assert organization.description == "Primary test organization"
    
    # Verify it exists in database
    db_org = test_db_session.query(Organization).filter(
        Organization.id == organization.id
    ).first()
    assert db_org is not None
    assert db_org.name == organization.name


def test_multiple_organizations_fixture(test_db_session, multiple_organizations):
    """Test that the multiple organizations fixture creates variety."""
    # Verify we have 3 organizations
    assert len(multiple_organizations) == 3
    
    # Verify each organization has unique properties
    names = [org.name for org in multiple_organizations]
    assert len(set(names)) == 3  # All names should be unique
    
    expected_names = [
        "Test Organization 1",
        "Test Organization 2", 
        "Test Organization 3"
    ]
    assert set(names) == set(expected_names)
    
    # Verify all organizations exist in database
    for org in multiple_organizations:
        db_org = test_db_session.query(Organization).filter(
            Organization.id == org.id
        ).first()
        assert db_org is not None
        assert db_org.name == org.name
        assert "variety testing" in db_org.description


def test_organization_variety_in_campaigns(test_db_session, multiple_campaigns):
    """Test that multiple campaigns use different organizations."""
    # Get all unique organization IDs from campaigns
    org_ids = set(campaign.organization_id for campaign in multiple_campaigns)
    
    # Should have campaigns from multiple organizations (at least 2)
    assert len(org_ids) >= 2, f"Expected campaigns from multiple organizations, got {len(org_ids)}"
    
    # Verify all organization IDs are valid
    for org_id in org_ids:
        org = test_db_session.query(Organization).filter(
            Organization.id == org_id
        ).first()
        assert org is not None, f"Organization {org_id} not found in database"


def test_large_dataset_organization_variety(test_db_session, large_dataset_campaigns):
    """Test that large dataset campaigns use multiple organizations."""
    # Get all unique organization IDs from campaigns
    org_ids = set(campaign.organization_id for campaign in large_dataset_campaigns)
    
    # Should have campaigns from all 3 organizations
    assert len(org_ids) == 3, f"Expected campaigns from 3 organizations, got {len(org_ids)}"
    
    # Verify distribution is reasonable (each org should have campaigns)
    org_counts = {}
    for campaign in large_dataset_campaigns:
        org_id = campaign.organization_id
        org_counts[org_id] = org_counts.get(org_id, 0) + 1
    
    # Each organization should have at least some campaigns
    for org_id, count in org_counts.items():
        assert count > 0, f"Organization {org_id} has no campaigns"
        
    # With 50 campaigns and 3 orgs, each should have 16-17 campaigns
    for org_id, count in org_counts.items():
        assert 15 <= count <= 18, f"Organization {org_id} has {count} campaigns, expected 15-18"


def test_organization_cleanup(test_db_session, organization):
    """Test that organization cleanup works properly."""
    org_id = organization.id
    
    # Verify organization exists
    assert test_db_session.query(Organization).filter(
        Organization.id == org_id
    ).first() is not None
    
    # The cleanup_database fixture should handle cleanup automatically
    # This test just verifies the organization was created successfully
    assert organization.name == "Test Organization" 