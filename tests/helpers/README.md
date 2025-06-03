# Database Verification Helpers

This package provides comprehensive database verification helpers for testing campaign API functionality. These helpers enable direct database access to verify that API operations have the expected database effects.

## Overview

The database helpers provide a clean, reliable way to:
- Verify campaign records exist with expected values
- Check campaign and job status changes
- Validate database relationships and constraints
- Ensure proper timestamp handling
- Clean up test data between tests
- Create test data directly in the database

## Core Components

### DatabaseHelpers Class

The main `DatabaseHelpers` class provides all verification functionality:

```python
from tests.helpers.database_helpers import DatabaseHelpers

# Initialize with database session
helpers = DatabaseHelpers(db_session)

# Verify campaign exists with expected values
campaign = helpers.verify_campaign_in_db(campaign_id, {
    "name": "Expected Name",
    "status": "created",
    "totalRecords": 100
})

# Verify job was created for campaign
job = helpers.verify_job_created_for_campaign(campaign_id, "FETCH_LEADS")

# Clean up test data
result = helpers.cleanup_test_data()
```

### Convenience Functions

For backward compatibility and ease of use:

```python
from tests.helpers import (
    verify_campaign_in_db,
    count_campaigns_in_db,
    cleanup_test_data
)

# Use directly with database session
verify_campaign_in_db(db_session, campaign_id, expected_data)
count = count_campaigns_in_db(db_session)
cleanup_test_data(db_session)
```

## Key Features

### Campaign Verification
- `verify_campaign_in_db()` - Verify campaign exists with expected field values
- `verify_campaign_not_in_db()` - Verify campaign was deleted or doesn't exist
- `verify_campaign_status_in_db()` - Check specific campaign status
- `verify_campaign_timestamps()` - Validate created_at/updated_at timestamps
- `get_campaign_by_field()` - Find campaign by any field value

### Job Verification
- `verify_job_created_for_campaign()` - Verify background job was created
- `verify_job_status_in_db()` - Check job status
- `get_campaign_jobs_from_db()` - Get all jobs for a campaign
- `create_test_job_in_db()` - Create job directly in database

### Database Management
- `count_campaigns_in_db()` - Count total campaigns
- `cleanup_test_data()` - Remove all test data
- `verify_no_orphaned_jobs()` - Check for orphaned job records
- `create_test_campaign_in_db()` - Create campaign directly in database

### Error Handling
- Clear, descriptive assertion messages
- Proper enum value handling (CampaignStatus, JobStatus, JobType)
- Datetime comparison support
- Comprehensive error reporting

## Usage Examples

### Basic Campaign Testing
```python
def test_campaign_creation(db_helpers):
    # Create campaign via API
    response = client.post("/api/v1/campaigns/", json=campaign_data)
    campaign_id = response.json()["id"]
    
    # Verify in database
    db_helpers.verify_campaign_in_db(campaign_id, {
        "name": campaign_data["name"],
        "status": "created"
    })
    
    # Verify timestamps
    db_helpers.verify_campaign_timestamps(campaign_id)
```

### Job Verification
```python
def test_campaign_with_jobs(db_helpers):
    # Create campaign and job
    campaign = db_helpers.create_test_campaign_in_db({"name": "Test"})
    job = db_helpers.create_test_job_in_db(campaign.id, {
        "job_type": "FETCH_LEADS",
        "status": "pending"
    })
    
    # Verify job exists
    db_helpers.verify_job_created_for_campaign(campaign.id, "FETCH_LEADS")
    db_helpers.verify_job_status_in_db(job.id, "pending")
```

### API Integration Testing
```python
def test_api_with_database_verification(db_helpers):
    # Test API operations with database verification
    response = client.post("/api/v1/campaigns/", json=data)
    campaign_id = response.json()["id"]
    
    # Verify API response matches database
    db_campaign = db_helpers.verify_campaign_in_db(campaign_id)
    assert response.json()["name"] == db_campaign.name
    
    # Update via API
    client.patch(f"/api/v1/campaigns/{campaign_id}", json={"name": "Updated"})
    
    # Verify update in database
    db_helpers.verify_campaign_in_db(campaign_id, {"name": "Updated"})
```

### Cleanup and Error Testing
```python
def test_cleanup_and_errors(db_helpers):
    # Create test data
    campaign = db_helpers.create_test_campaign_in_db({"name": "Test"})
    
    # Test error cases
    with pytest.raises(AssertionError):
        db_helpers.verify_campaign_in_db("fake-id")
    
    # Clean up
    result = db_helpers.cleanup_test_data()
    assert result["campaigns_deleted"] == 1
    
    # Verify cleanup
    db_helpers.verify_campaign_not_in_db(campaign.id)
```

## Testing the Helpers

The helpers themselves are thoroughly tested in `tests/test_database_helpers.py`:

```bash
# Run helper tests
pytest tests/test_database_helpers.py -v

# Run integration tests
pytest tests/test_helpers_integration.py -v
```

## Best Practices

1. **Use in fixtures**: Create `db_helpers` fixture for consistent usage
2. **Clean up**: Always clean test data between tests
3. **Verify state**: Check database state after API operations
4. **Handle sessions**: Refresh sessions when testing across transactions
5. **Clear assertions**: Use specific expected values for better error messages
6. **Test errors**: Verify helpers catch incorrect states properly

## Integration with Existing Tests

The helpers integrate seamlessly with existing test infrastructure:

```python
@pytest.fixture
def db_helpers(db_session):
    """Create DatabaseHelpers instance for testing."""
    return DatabaseHelpers(db_session)

def test_existing_functionality(db_helpers):
    # Use helpers alongside existing test patterns
    # Provides additional verification layer
    pass
```

This ensures comprehensive testing that verifies both API responses and actual database state changes. 