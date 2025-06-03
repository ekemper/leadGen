# Campaign Business Logic Migration Plan

## Overview
This document provides detailed step-by-step instructions for migrating campaign business logic from the deprecated Flask application to the current FastAPI application (`fastapi-k8-proto`). The migration preserves only the business logic while adapting to FastAPI patterns and conventions.

## Migration Scope
- **Source Files**: `depricated-routes.py`, `depricated-campaign-service.py`, `depricated-campaign-model.py`, `depricated-campaign-tests.py`
- **Target**: FastAPI application following existing patterns in `app/` directory
- **Preserve**: Business logic, data structures, validation rules, API contracts
- **Adapt**: Framework patterns, dependency injection, async/await, Pydantic schemas, SQLAlchemy models

## Prerequisites
- Current FastAPI app is running and healthy
- Database is accessible and migrations are up to date
- Redis and Celery are configured and running
- Test environment is set up

---

## Phase 1: Model Migration

### Step 1.1: Create Campaign Status Enum
**Goal**: Create the campaign status enumeration following FastAPI patterns

**Actions**:
1. Create `app/models/campaign_status.py`
2. Define `CampaignStatus` enum with values: `CREATED`, `RUNNING`, `COMPLETED`, `FAILED`
3. Use Python's `enum.Enum` with string values

**Validation Strategy**:
- Import the enum in Python REPL
- Verify all status values are accessible
- Check string representation matches expected values

**Expected Code Structure**:
```python
import enum

class CampaignStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Step 1.2: Create Campaign Model
**Goal**: Create the Campaign SQLAlchemy model following existing patterns

**Actions**:
1. Create `app/models/campaign.py`
2. Define Campaign model inheriting from `Base`
3. Include all fields from deprecated model: `id`, `name`, `description`, `status`, `created_at`, `updated_at`, `organization_id`, `status_message`, `status_error`, `completed_at`, `failed_at`, `fileName`, `totalRecords`, `url`, `instantly_campaign_id`
4. Use UUID for primary key (String type)
5. Add status transition validation methods
6. Add `to_dict()` method for serialization

**Validation Strategy**:
- Create database migration: `alembic revision --autogenerate -m "Add campaign model"`
- Run migration: `alembic upgrade head`
- Verify table creation in database
- Test model creation in Python REPL

### Step 1.3: Update Models __init__.py
**Goal**: Export the new Campaign model

**Actions**:
1. Add import for Campaign model in `app/models/__init__.py`
2. Add import for CampaignStatus enum

**Validation Strategy**:
- Import models in Python REPL: `from app.models import Campaign, CampaignStatus`
- Verify no import errors

---

## Phase 2: Schema Migration

### Step 2.1: Create Campaign Schemas
**Goal**: Create Pydantic schemas for request/response validation

**Actions**:
1. Create `app/schemas/campaign.py`
2. Define schemas following existing job schema patterns:
   - `CampaignBase`: Common fields
   - `CampaignCreate`: Fields required for creation
   - `CampaignUpdate`: Fields allowed for updates
   - `CampaignInDB`: Database representation
   - `CampaignResponse`: API response format
   - `CampaignStart`: Schema for starting campaigns

**Validation Strategy**:
- Test schema validation in Python REPL
- Validate required fields are enforced
- Test optional fields work correctly
- Verify serialization/deserialization

### Step 2.2: Update Schemas __init__.py
**Goal**: Export campaign schemas

**Actions**:
1. Add campaign schema imports to `app/schemas/__init__.py`

**Validation Strategy**:
- Import schemas in Python REPL
- Verify no import errors

---

## Phase 3: Service Layer Migration

### Step 3.1: Create Campaign Service
**Goal**: Migrate business logic from CampaignService to FastAPI patterns

**Actions**:
1. Create `app/services/campaign.py`
2. Migrate core business methods:
   - `get_campaigns()`: List all campaigns
   - `get_campaign(campaign_id)`: Get single campaign
   - `create_campaign(data)`: Create new campaign
   - `update_campaign(campaign_id, data)`: Update campaign
   - `start_campaign(campaign_id)`: Start campaign process
   - `validate_search_url(url)`: URL validation
   - `validate_count(count)`: Count validation
   - `cleanup_campaign_jobs(campaign_id, days)`: Job cleanup
   - `get_campaign_lead_stats(campaign_id)`: Lead statistics
   - `get_campaign_instantly_analytics(campaign)`: Analytics integration
3. Adapt to use SQLAlchemy session dependency injection
4. Remove Flask-specific imports and patterns
5. Use async/await where appropriate
6. Implement proper error handling with FastAPI HTTPException

**Validation Strategy**:
- Unit test each method individually
- Test database operations with test database
- Verify error handling works correctly
- Test async functionality

### Step 3.2: Create Service Dependencies
**Goal**: Set up dependency injection for services

**Actions**:
1. Create `app/core/dependencies.py` if it doesn't exist
2. Add campaign service dependency function
3. Follow existing patterns for database session injection

**Validation Strategy**:
- Test dependency injection in endpoint context
- Verify service instantiation works correctly

---

## Phase 4: API Endpoints Migration

### Step 4.1: Create Campaign Router
**Goal**: Create FastAPI router with campaign endpoints

**Actions**:
1. Create `app/api/endpoints/campaigns.py`
2. Migrate endpoints following existing job router patterns:
   - `GET /campaigns`: List campaigns
   - `POST /campaigns`: Create campaign
   - `GET /campaigns/{campaign_id}`: Get campaign
   - `PATCH /campaigns/{campaign_id}`: Update campaign
   - `POST /campaigns/{campaign_id}/start`: Start campaign
   - `GET /campaigns/{campaign_id}/details`: Get campaign details
   - `POST /campaigns/{campaign_id}/cleanup`: Cleanup jobs
   - `GET /campaigns/{campaign_id}/results`: Get campaign results
3. Use proper FastAPI decorators and dependency injection
4. Implement request/response models with Pydantic schemas
5. Add proper HTTP status codes
6. Remove Flask-specific authentication (will be added later)
7. Add proper error handling with HTTPException

**Validation Strategy**:
- Test each endpoint with FastAPI test client
- Verify request/response schemas work correctly
- Test error cases return proper HTTP status codes
- Validate database operations work correctly

### Step 4.2: Update Main App Router
**Goal**: Include campaign router in main application

**Actions**:
1. Update `app/main.py` to include campaign router
2. Add campaigns router with proper prefix and tags

**Validation Strategy**:
- Start FastAPI server
- Check OpenAPI docs at `/docs` include campaign endpoints
- Test basic endpoint accessibility

---

## Phase 5: Background Task Integration

### Step 5.1: Create Campaign Tasks
**Goal**: Migrate background job processing to Celery

**Actions**:
1. Create `app/workers/campaign_tasks.py`
2. Migrate task functions:
   - `fetch_and_save_leads_task`: Apollo integration task
   - `cleanup_campaign_jobs_task`: Job cleanup task
3. Adapt to use Celery patterns from existing worker tasks
4. Update job creation to use new task functions

**Validation Strategy**:
- Test task registration with Celery
- Verify tasks can be queued and executed
- Test task result handling
- Monitor Celery worker logs for errors

### Step 5.2: Update Job Model for Campaigns
**Goal**: Extend job model to support campaign-specific job types

**Actions**:
1. Update `app/models/job.py` to add campaign-related job types
2. Add foreign key relationship to campaigns if needed
3. Create database migration for changes

**Validation Strategy**:
- Run database migration
- Test job creation with campaign context
- Verify relationships work correctly

---

## Phase 6: Functional API Testing Migration

### Step 6.1: Create Comprehensive Campaign API Tests
**Goal**: Create comprehensive functional tests that hit API endpoints and verify database state

**Actions**:
1. Create `tests/test_campaigns_api.py`
2. Migrate and expand test cases from deprecated tests with database verification:
   - **Campaign Creation Tests**:
     - Test successful campaign creation with all required fields
     - Verify campaign record exists in database with correct values
     - Test validation errors for missing/invalid fields
     - Verify no database records created on validation failures
   - **Campaign Listing Tests**:
     - Test empty campaign list returns correctly
     - Create multiple campaigns and verify list endpoint returns all
     - Test pagination and filtering if implemented
     - Verify database query efficiency
   - **Campaign Retrieval Tests**:
     - Test successful retrieval of existing campaign
     - Verify returned data matches database record exactly
     - Test 404 error for non-existent campaign ID
     - Test malformed campaign ID handling
   - **Campaign Update Tests**:
     - Test successful update of allowed fields (name, description, etc.)
     - Verify database record is updated correctly
     - Test partial updates work correctly
     - Test validation errors for invalid update data
     - Test 404 error for non-existent campaign
     - Verify immutable fields cannot be changed
   - **Campaign Start Flow Tests**:
     - Test starting campaign changes status from CREATED to RUNNING
     - Verify database status update is persisted
     - Verify background job is created in jobs table
     - Test error when trying to start non-CREATED campaign
     - Test concurrent start attempts are handled correctly
   - **Campaign Details Tests**:
     - Test campaign details endpoint returns campaign + stats
     - Verify lead statistics are calculated correctly from database
     - Test analytics integration data is included
     - Test error handling when analytics service fails
   - **Campaign Cleanup Tests**:
     - Create old jobs and verify cleanup removes them from database
     - Test cleanup respects date cutoff correctly
     - Verify active jobs are not removed
     - Test cleanup with no old jobs returns appropriate response
   - **Security and Edge Case Tests**:
     - Test XSS prevention in campaign names/descriptions
     - Verify special characters are handled correctly
     - Test extremely long field values
     - Test SQL injection prevention
     - Test concurrent operations on same campaign
3. Use FastAPI TestClient for all API calls
4. Use real database connection (not mocked) for verification
5. Create comprehensive database verification helpers
6. Use pytest fixtures for test data setup and cleanup
7. Follow existing test patterns from `tests/test_health.py`

**Validation Strategy**:
- Run individual test functions: `pytest tests/test_campaigns_api.py::test_create_campaign_success -v`
- Run full test suite: `pytest tests/test_campaigns_api.py -v`
- Verify all tests pass
- Check that database state is verified in each test
- Ensure test database is properly cleaned between tests
- Verify no test data leaks between test runs

### Step 6.2: Create Database Verification Helpers
**Goal**: Create utility functions for comprehensive database state verification

**Actions**:
1. Create `tests/helpers/database_helpers.py`
2. Implement helper functions:
   - `verify_campaign_in_db(campaign_id, expected_data)`: Verify campaign exists with expected values
   - `verify_campaign_not_in_db(campaign_id)`: Verify campaign was not created/was deleted
   - `count_campaigns_in_db()`: Count total campaigns in database
   - `verify_job_created_for_campaign(campaign_id, job_type)`: Verify background job was created
   - `get_campaign_jobs_from_db(campaign_id)`: Get all jobs for a campaign
   - `verify_campaign_status_in_db(campaign_id, expected_status)`: Verify status in database
   - `cleanup_test_data()`: Clean all test data from database
   - `create_test_campaign_in_db(data)`: Create campaign directly in database for testing
3. Use direct database queries to verify state
4. Include comprehensive assertions with clear error messages
5. Handle database connection and session management properly

**Validation Strategy**:
- Test each helper function individually
- Verify helpers work with test database
- Test error handling in helper functions
- Ensure helpers don't interfere with application code

### Step 6.3: Create Test Data Fixtures and Setup
**Goal**: Create comprehensive test data management and fixtures

**Actions**:
1. Create `tests/fixtures/campaign_fixtures.py`
2. Implement pytest fixtures:
   - `test_db_session`: Database session for tests
   - `clean_database`: Fixture to clean database before/after tests
   - `sample_campaign_data`: Valid campaign creation data
   - `invalid_campaign_data`: Various invalid data scenarios
   - `existing_campaign`: Pre-created campaign for testing
   - `multiple_campaigns`: Multiple campaigns for list testing
   - `campaign_with_jobs`: Campaign with associated jobs
   - `old_jobs_for_cleanup`: Old jobs for cleanup testing
3. Ensure proper test isolation
4. Handle database transactions correctly
5. Provide comprehensive test data scenarios

**Validation Strategy**:
- Test fixtures work correctly in isolation
- Verify database cleanup works properly
- Test fixture dependencies work correctly
- Ensure no data leakage between tests

---

## Phase 7: End-to-End Integration Testing

### Step 7.1: Complete Campaign Workflow Tests
**Goal**: Test complete campaign workflow with real background processing

**Actions**:
1. Create `tests/test_campaign_e2e.py`
2. Test full campaign lifecycle with database and Celery verification:
   - **Complete Campaign Flow**:
     - Create campaign via API and verify in database
     - Start campaign via API and verify status change in database
     - Verify background job is created and queued in Celery
     - Monitor job execution and verify completion in database
     - Verify campaign status updates throughout the process
     - Test campaign cleanup and verify jobs are removed from database
   - **Error Recovery Testing**:
     - Test campaign failure scenarios and verify error states in database
     - Test job failure handling and campaign status updates
     - Test system recovery after failures
   - **Concurrent Operations Testing**:
     - Test multiple campaigns running simultaneously
     - Verify database consistency with concurrent operations
     - Test resource contention scenarios
3. Use real database and Celery workers (not mocked)
4. Include comprehensive database state verification at each step
5. Test with realistic data volumes and timing

**Validation Strategy**:
- Run integration test: `pytest tests/test_campaign_e2e.py -v`
- Monitor Celery worker logs for job execution
- Verify database state at each step of the workflow
- Check for any data inconsistencies or race conditions
- Verify proper cleanup of test data

### Step 7.2: Cross-Endpoint API Workflow Tests
**Goal**: Test complex workflows that span multiple API endpoints

**Actions**:
1. Add workflow tests to `tests/test_campaigns_api.py`
2. Test complex API interaction scenarios:
   - **Campaign Lifecycle via API**:
     - Create → Update → Start → Monitor → Cleanup sequence
     - Verify each API call affects database correctly
     - Test error handling at each step
   - **Bulk Operations Testing**:
     - Create multiple campaigns and verify list endpoint
     - Test batch operations if implemented
     - Verify database performance with multiple records
   - **Data Consistency Testing**:
     - Test campaign details endpoint after various operations
     - Verify analytics data consistency
     - Test lead statistics accuracy
3. Focus on API-to-database consistency
4. Test realistic user workflows
5. Verify proper HTTP status codes and error responses

**Validation Strategy**:
- Run workflow tests as part of main API test suite
- Verify database state matches API responses at each step
- Test error scenarios return proper HTTP codes
- Ensure workflows work with realistic data volumes

---

## Phase 8: External Service Integration

### Step 8.1: Apollo Service Integration
**Goal**: Integrate Apollo service for lead fetching

**Actions**:
1. Create `app/services/apollo.py` if not exists
2. Migrate Apollo service integration from deprecated code
3. Adapt to FastAPI patterns and async/await
4. Add proper error handling and logging

**Validation Strategy**:
- Test Apollo service connection
- Verify lead fetching functionality
- Test error scenarios (API failures, rate limits)

### Step 8.2: Instantly Service Integration
**Goal**: Integrate Instantly service for email campaigns

**Actions**:
1. Create `app/services/instantly.py` if not exists
2. Migrate Instantly service integration
3. Test campaign creation and analytics retrieval

**Validation Strategy**:
- Test Instantly service connection
- Verify campaign creation works
- Test analytics data retrieval

---

## Phase 9: Database Migration and Cleanup

### Step 9.1: Create Production Migration
**Goal**: Create database migration for production deployment

**Actions**:
1. Generate final migration: `alembic revision --autogenerate -m "Add campaign functionality"`
2. Review migration script for correctness
3. Test migration on copy of production data

**Validation Strategy**:
- Run migration on test database
- Verify all tables and constraints are created correctly
- Test rollback functionality
- Validate data integrity

### Step 9.2: Update Database Initialization
**Goal**: Ensure campaign tables are created in fresh installations

**Actions**:
1. Update any database initialization scripts
2. Verify campaign models are included in Base metadata

**Validation Strategy**:
- Test fresh database creation
- Verify all tables are created correctly

---

## Phase 10: Documentation and Deployment

### Step 10.1: Update API Documentation
**Goal**: Ensure campaign endpoints are properly documented

**Actions**:
1. Add docstrings to all campaign endpoints
2. Verify OpenAPI schema generation is correct
3. Test API documentation at `/docs`

**Validation Strategy**:
- Review generated API docs
- Test example requests/responses
- Verify schema validation works in docs

### Step 10.2: Update Configuration
**Goal**: Add any new configuration needed for campaigns

**Actions**:
1. Update `app/core/config.py` if new settings are needed
2. Update environment variable documentation
3. Update Docker configuration if needed

**Validation Strategy**:
- Test configuration loading
- Verify all required settings are available
- Test with different environment configurations

---

## Phase 11: Performance and Security Testing

### Step 11.1: Performance Testing
**Goal**: Ensure campaign endpoints perform adequately

**Actions**:
1. Create performance tests for campaign endpoints
2. Test with large datasets
3. Monitor database query performance
4. Test concurrent campaign operations

**Validation Strategy**:
- Run load tests on campaign endpoints
- Monitor response times and resource usage
- Verify database performance is acceptable

### Step 11.2: Security Testing
**Goal**: Ensure campaign functionality is secure

**Actions**:
1. Test input validation and sanitization
2. Verify SQL injection protection
3. Test XSS prevention
4. Validate authorization controls (when auth is added)

**Validation Strategy**:
- Run security test suite
- Test malicious input scenarios
- Verify proper error handling without information leakage

---

## Phase 12: Final Validation and Cleanup

### Step 12.1: Full System Test
**Goal**: Verify entire system works correctly with campaigns

**Actions**:
1. Run complete test suite: `pytest tests/ -v`
2. Test all campaign functionality manually
3. Verify no regressions in existing functionality
4. Test error scenarios and edge cases

**Validation Strategy**:
- All tests pass
- Manual testing confirms functionality
- No errors in application logs
- Database state is consistent

### Step 12.2: Code Review and Cleanup
**Goal**: Ensure code quality and consistency

**Actions**:
1. Review all migrated code for consistency with FastAPI patterns
2. Remove any remaining Flask-specific patterns
3. Ensure proper error handling throughout
4. Verify logging is consistent
5. Check code formatting and style

**Validation Strategy**:
- Code review checklist completion
- Linting passes without errors
- Type checking passes (if using mypy)
- Documentation is complete

### Step 12.3: Deployment Preparation
**Goal**: Prepare for production deployment

**Actions**:
1. Create deployment checklist
2. Update deployment scripts if needed
3. Prepare rollback plan
4. Update monitoring and alerting for campaign functionality

**Validation Strategy**:
- Deployment scripts work correctly
- Monitoring captures campaign metrics
- Rollback procedures are tested
- Production readiness checklist is complete

---

## Success Criteria

The migration is considered successful when:

1. **Functionality**: All campaign business logic works correctly in FastAPI
2. **Tests**: All tests pass and provide adequate coverage
3. **Performance**: Campaign operations perform within acceptable limits
4. **Security**: All security requirements are met
5. **Documentation**: API documentation is complete and accurate
6. **Integration**: Campaign functionality integrates properly with existing systems
7. **Deployment**: System can be deployed to production without issues

## Rollback Plan

If issues are discovered during migration:

1. **Database**: Use Alembic to rollback database migrations
2. **Code**: Revert to previous Git commit
3. **Configuration**: Restore previous configuration files
4. **Services**: Restart services with previous version
5. **Monitoring**: Verify system returns to previous stable state

## Post-Migration Tasks

After successful migration:

1. **Monitoring**: Set up monitoring for campaign functionality
2. **Documentation**: Update user documentation
3. **Training**: Train team on new campaign functionality
4. **Optimization**: Monitor and optimize performance as needed
5. **Cleanup**: Remove deprecated files after verification period

---

## Notes for AI Agent

- **Error Handling**: If any step fails, stop and report the specific error with context
- **Validation**: Always run the validation strategy for each step before proceeding
- **Logging**: Monitor application logs during testing for any errors or warnings
- **Database**: Always backup database before running migrations
- **Dependencies**: Ensure all required dependencies are installed before starting
- **Environment**: Use appropriate environment (development/testing) for migration work
- **Git**: Commit changes after each major phase for easy rollback if needed 