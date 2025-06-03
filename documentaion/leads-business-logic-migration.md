# Leads Business Logic Migration Plan

## Overview
This document provides detailed step-by-step instructions for migrating the leads business logic from the Flask leadGen project to this FastAPI application (fastapi-k8-proto). The migration will preserve only the business logic while adapting to the current FastAPI patterns, conventions, and configurations.

## Source Files to Migrate
- `/Users/ek/dev/leadGen/server/api/services/lead_service.py` - Lead service business logic
- `/Users/ek/dev/leadGen/server/models/lead.py` - Lead model definition
- Lead routes from `depricated-routes.py` (lines 538-714)

## Target Structure
Following the existing FastAPI patterns:
- Model: `app/models/lead.py`
- Schema: `app/schemas/lead.py`
- Service: `app/services/lead.py`
- Endpoints: `app/api/endpoints/leads.py`
- Tests: `tests/test_leads_api.py`

---

## Step 1: Examine Source Files
**Goal**: Understand the existing lead business logic and data structure from the Flask app.

**Actions**:
1. Read the lead model from the source Flask app
2. Read the lead service from the source Flask app
3. Analyze the business logic patterns and data relationships

**Commands to Run**:
```bash
# Read the source lead model
cat /Users/ek/dev/leadGen/server/models/lead.py

# Read the source lead service
cat /Users/ek/dev/leadGen/server/api/services/lead_service.py
```

**Success Criteria**:
- Understand the lead data structure (fields, relationships)
- Identify core business logic methods
- Understand validation rules and constraints
- Document any external dependencies or integrations

---

## Step 2: Create Lead Model
**Goal**: Create the SQLAlchemy model for leads following the existing FastAPI patterns.

**Actions**:
1. Create `app/models/lead.py` following the pattern from `app/models/campaign.py`
2. Define the Lead model with appropriate fields, relationships, and constraints
3. Add the model to the imports in `app/models/__init__.py`

**Code Changes**:
- Create `app/models/lead.py` with SQLAlchemy model definition
- Update `app/models/__init__.py` to include Lead import

**Success Criteria**:
- Lead model follows FastAPI/SQLAlchemy patterns
- All necessary fields are defined with proper types
- Relationships to campaigns/organizations are established
- Model includes helper methods like `to_dict()` if needed

**Verification**:
```bash
# Check model syntax
python -c "from app.models.lead import Lead; print('Lead model imported successfully')"
```

---

## Step 3: Create Lead Schemas
**Goal**: Create Pydantic schemas for lead data validation and serialization.

**Actions**:
1. Create `app/schemas/lead.py` following the pattern from `app/schemas/campaign.py`
2. Define schemas for:
   - `LeadBase` - Common fields
   - `LeadCreate` - Fields required for creation
   - `LeadUpdate` - Fields allowed for updates
   - `LeadResponse` - Fields returned in API responses
3. Add schema imports to `app/schemas/__init__.py`

**Code Changes**:
- Create `app/schemas/lead.py` with Pydantic schema definitions
- Update `app/schemas/__init__.py` to include lead schema imports

**Success Criteria**:
- Schemas follow FastAPI/Pydantic patterns
- Proper validation rules are defined
- Response schemas include computed fields if needed
- Schemas handle optional fields appropriately

**Verification**:
```bash
# Check schema syntax
python -c "from app.schemas.lead import LeadCreate, LeadResponse; print('Lead schemas imported successfully')"
```

---

## Step 4: Create Database Migration
**Goal**: Create Alembic migration to add the leads table to the database.

**Actions**:
1. Generate Alembic migration for the new Lead model
2. Review the generated migration for correctness
3. Apply the migration to create the leads table

**Commands to Run**:
```bash
# Generate migration (run in API docker container)
docker-compose exec api alembic revision --autogenerate -m "Add leads table"

# Review the generated migration file
ls alembic/versions/ | tail -1 | xargs -I {} cat alembic/versions/{}

# Apply migration
docker-compose exec api alembic upgrade head
```

**Success Criteria**:
- Migration file is generated successfully
- Migration includes all lead table columns and constraints
- Migration applies without errors
- Database contains the new leads table

**Verification**:
```bash
# Check table exists in database
docker-compose exec api python -c "
from app.core.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print('leads' in tables and 'Leads table exists' or 'Leads table missing')
"
```

---

## Step 5: Create Lead Service
**Goal**: Create the lead service with business logic following FastAPI patterns.

**Actions**:
1. Create `app/services/lead.py` following the pattern from `app/services/campaign.py`
2. Migrate business logic methods from the Flask lead service:
   - `get_leads()` - List leads with optional filtering
   - `get_lead()` - Get single lead by ID
   - `create_lead()` - Create new lead
   - `update_lead()` - Update existing lead
3. Adapt Flask patterns to FastAPI async patterns
4. Use SQLAlchemy sessions instead of Flask-SQLAlchemy

**Code Changes**:
- Create `app/services/lead.py` with business logic methods
- Ensure all methods are async and use proper session handling
- Include proper error handling and validation

**Success Criteria**:
- Service follows FastAPI async patterns
- All CRUD operations are implemented
- Proper error handling for not found, validation errors
- Service uses dependency injection for database sessions
- Business logic is preserved from Flask implementation

**Verification**:
```bash
# Check service syntax
python -c "from app.services.lead import LeadService; print('Lead service imported successfully')"
```

---

## Step 6: Create Lead Endpoints
**Goal**: Create FastAPI endpoints for lead operations.

**Actions**:
1. Create `app/api/endpoints/leads.py` following the pattern from `app/api/endpoints/campaigns.py`
2. Implement endpoints:
   - `GET /leads` - List leads with optional campaign_id filter
   - `POST /leads` - Create new lead
   - `GET /leads/{lead_id}` - Get specific lead
   - `PUT /leads/{lead_id}` - Update specific lead
3. Use proper FastAPI patterns for dependency injection, validation, and responses
4. Include proper HTTP status codes and error handling

**Code Changes**:
- Create `app/api/endpoints/leads.py` with FastAPI router and endpoints
- Follow existing patterns for authentication, validation, and responses

**Success Criteria**:
- All endpoints follow FastAPI patterns
- Proper request/response models are used
- HTTP status codes match REST conventions
- Error handling provides meaningful messages
- Endpoints use dependency injection for database sessions

**Verification**:
```bash
# Check endpoints syntax
python -c "from app.api.endpoints.leads import router; print('Lead endpoints imported successfully')"
```

---

## Step 7: Register Lead Routes
**Goal**: Register the lead endpoints with the FastAPI application.

**Actions**:
1. Update `app/main.py` to import and include the leads router
2. Add the leads router with appropriate prefix and tags

**Code Changes**:
- Add import for leads router in `app/main.py`
- Add `app.include_router()` call for leads

**Success Criteria**:
- Leads router is properly registered
- Routes are accessible under `/api/v1/leads`
- OpenAPI documentation includes lead endpoints

**Verification**:
```bash
# Start the application and check routes
docker-compose up -d api
curl -s http://localhost:8000/api/v1/docs | grep -q "leads" && echo "Leads routes registered" || echo "Leads routes missing"
```

---

## Step 8: Create Comprehensive API Tests
**Goal**: Create functional API tests that hit the endpoints and verify database state.

**Actions**:
1. Create `tests/test_leads_api.py` following the pattern from `tests/test_campaigns_api.py`
2. Implement test cases for:
   - Lead creation with validation
   - Lead listing with and without filters
   - Lead retrieval by ID
   - Lead updates
   - Error cases (not found, validation errors)
   - Database state verification for each operation
3. Include helper functions for database verification
4. Test campaign-lead relationships

**Code Changes**:
- Create comprehensive test suite in `tests/test_leads_api.py`
- Include fixtures for test data setup
- Add database verification helpers

**Success Criteria**:
- All CRUD operations are tested
- Tests verify both API responses and database state
- Error cases are properly tested
- Tests follow existing patterns from campaign tests
- Tests are isolated and can run independently

**Verification**:
```bash
# Run lead API tests
docker-compose exec api python -m pytest tests/test_leads_api.py -v
```

---

## Step 9: Test Lead-Campaign Integration
**Goal**: Verify that leads properly integrate with existing campaign functionality.

**Actions**:
1. Create integration tests that verify lead-campaign relationships
2. Test filtering leads by campaign_id
3. Test that campaign deletion handles associated leads appropriately
4. Verify foreign key constraints work correctly

**Code Changes**:
- Add integration tests to `tests/test_leads_api.py` or create separate integration test file
- Test cross-entity relationships and constraints

**Success Criteria**:
- Leads can be properly associated with campaigns
- Filtering by campaign_id works correctly
- Foreign key constraints are enforced
- Cascade behaviors work as expected

**Verification**:
```bash
# Run integration tests
docker-compose exec api python -m pytest tests/test_leads_api.py::test_lead_campaign_integration -v
```

---

## Step 10: Validate Complete API Functionality
**Goal**: Perform end-to-end testing of the complete leads API.

**Actions**:
1. Test complete CRUD workflow through API calls
2. Verify all endpoints return correct HTTP status codes
3. Test error handling and validation
4. Verify OpenAPI documentation is complete and accurate

**Commands to Run**:
```bash
# Test complete workflow
docker-compose exec api python -c "
import requests
import json

base_url = 'http://localhost:8000/api/v1'

# Test lead creation
lead_data = {
    'name': 'Test Lead',
    'email': 'test@example.com',
    'campaign_id': 'some-campaign-id'
}
response = requests.post(f'{base_url}/leads', json=lead_data)
print(f'Create lead: {response.status_code}')

# Test lead listing
response = requests.get(f'{base_url}/leads')
print(f'List leads: {response.status_code}')

# Test OpenAPI docs
response = requests.get(f'{base_url}/docs')
print(f'OpenAPI docs: {response.status_code}')
"
```

**Success Criteria**:
- All API endpoints respond correctly
- CRUD operations work end-to-end
- Error handling provides appropriate responses
- OpenAPI documentation is complete
- Database state is consistent after operations

---

## Step 11: Run Full Test Suite
**Goal**: Ensure the new leads functionality doesn't break existing functionality.

**Actions**:
1. Run the complete test suite to ensure no regressions
2. Fix any test failures or conflicts
3. Verify all existing functionality still works

**Commands to Run**:
```bash
# Run full test suite
docker-compose exec api python -m pytest tests/ -v

# Run specific test categories
docker-compose exec api python -m pytest tests/test_campaigns_api.py -v
docker-compose exec api python -m pytest tests/test_organizations_api.py -v
docker-compose exec api python -m pytest tests/test_leads_api.py -v
```

**Success Criteria**:
- All existing tests continue to pass
- New lead tests pass
- No regressions in existing functionality
- Test coverage is maintained or improved

---

## Step 12: Performance and Load Testing
**Goal**: Verify the leads API performs adequately under load.

**Actions**:
1. Test API response times for lead operations
2. Test database performance with larger datasets
3. Verify memory usage and resource consumption

**Commands to Run**:
```bash
# Basic performance test
docker-compose exec api python -c "
import time
import requests

base_url = 'http://localhost:8000/api/v1'

# Time lead listing
start = time.time()
response = requests.get(f'{base_url}/leads')
end = time.time()
print(f'Lead listing took {end - start:.3f} seconds')

# Time lead creation
start = time.time()
response = requests.post(f'{base_url}/leads', json={'name': 'Perf Test', 'email': 'perf@test.com'})
end = time.time()
print(f'Lead creation took {end - start:.3f} seconds')
"
```

**Success Criteria**:
- API responses are within acceptable time limits
- Database queries are optimized
- Memory usage is reasonable
- No performance regressions in existing functionality

---

## Step 13: Documentation and Cleanup
**Goal**: Ensure proper documentation and clean up any temporary files.

**Actions**:
1. Update API documentation if needed
2. Add any necessary comments to complex business logic
3. Remove any temporary files or debug code
4. Update README if new dependencies were added

**Success Criteria**:
- Code is properly documented
- No debug code or temporary files remain
- Documentation is up to date
- Code follows project conventions

---

## Step 14: Final Verification
**Goal**: Perform final end-to-end verification of the complete migration.

**Actions**:
1. Restart all services to ensure clean state
2. Run complete test suite one final time
3. Verify all lead endpoints work correctly
4. Check database state is clean and consistent

**Commands to Run**:
```bash
# Restart services
docker-compose down
docker-compose up -d

# Wait for services to be ready
sleep 10

# Run final test suite
docker-compose exec api python -m pytest tests/ -v

# Verify API is accessible
curl -f http://localhost:8000/api/v1/leads && echo "Leads API accessible" || echo "Leads API not accessible"

# Check database state
docker-compose exec api python -c "
from app.core.database import SessionLocal
from app.models.lead import Lead
db = SessionLocal()
count = db.query(Lead).count()
print(f'Leads table accessible, contains {count} records')
db.close()
"
```

**Success Criteria**:
- All services start successfully
- Complete test suite passes
- All API endpoints are accessible
- Database is in consistent state
- No errors in application logs

---

## Rollback Plan
If any step fails and cannot be resolved:

1. **Database Rollback**: Use Alembic to downgrade the migration
   ```bash
   docker-compose exec api alembic downgrade -1
   ```

2. **Code Rollback**: Remove the added files and revert changes
   ```bash
   rm -f app/models/lead.py
   rm -f app/schemas/lead.py
   rm -f app/services/lead.py
   rm -f app/api/endpoints/leads.py
   rm -f tests/test_leads_api.py
   # Revert changes to app/main.py and app/models/__init__.py
   ```

3. **Restart Services**: Ensure system returns to previous working state
   ```bash
   docker-compose down
   docker-compose up -d
   ```

---

## Success Metrics
The migration is considered successful when:

1. ✅ All lead CRUD operations work through the API
2. ✅ Database contains properly structured leads table
3. ✅ All tests pass (existing + new lead tests)
4. ✅ API documentation includes lead endpoints
5. ✅ No regressions in existing functionality
6. ✅ Lead-campaign relationships work correctly
7. ✅ Error handling provides meaningful responses
8. ✅ Performance is within acceptable limits

---

## Notes for AI Agent
- Always run database operations in the API docker container
- Use the existing patterns from campaigns/organizations as templates
- Preserve business logic while adapting to FastAPI patterns
- Test each step thoroughly before proceeding to the next
- If any step fails, investigate and resolve before continuing
- Document any deviations from the plan and reasons for changes 