# PROJECT NAME REPLACEMENT PLAN - COMPLETED ✅

**Status**: ✅ **COMPLETED SUCCESSFULLY**  
**Date Completed**: June 3, 2025  
**Total Duration**: ~2 hours  

## Completion Summary

All phases of the project name replacement from `fastapi-k8-proto` to `lead-gen` have been successfully completed. The migration involved:

- ✅ **8 Phases Completed**: All planned phases executed successfully
- ✅ **15+ Files Updated**: Infrastructure, application code, documentation, and test files
- ✅ **Zero Breaking Changes**: All tests pass, containers running with new names
- ✅ **Database Migration**: PostgreSQL database name updated from `fastapi_k8_proto` to `lead_gen`
- ✅ **Container Names**: All containers now use `leadgen-*` naming convention
- ✅ **Service Identity**: API health endpoint returns `"lead-gen"` as service name
- ✅ **Documentation Updated**: All migration guides and documentation reflect new naming

### Key Changes Made:
1. **Infrastructure**: docker-compose.prod.yml, alembic.ini, scripts/docker-dev.sh
2. **Application Code**: health.py service name, test assertions
3. **Background Services**: database connection strings, Redis host references
4. **Scripts**: reset_and_run_concurrent_campaigns_test.sh container references
5. **Documentation**: All .md files in documentaion/ directory
6. **Test Files**: Sample outputs and integration test configurations

### Verification Results:
- ✅ Health tests passing
- ✅ Containers running with correct names (`leadgen-*`)
- ✅ Database connections working with new database name
- ✅ No remaining `fastapi-k8-proto` references in codebase (except this plan file)

---

## Original Plan (Completed)

# Project Name Replacement Plan: fastapi-k8-proto → lead-gen

## Overview

This document provides comprehensive step-by-step instructions for an AI agent to replace all occurrences of `fastapi-k8-proto` with `lead-gen` throughout the entire project codebase. This replacement ensures consistent naming and removes references to the previous project structure.

## General Rules and Instructions

### Critical Assessment Protocol
- **Always make a technical, critical assessment** for any queries, statements, ideas, or questions. Don't be afraid to question the user's plan.
- **Always ask for clarification** if needed from the user when implementing the steps of the plan.
- **NEVER MAKE ASSUMPTIONS** - always provide rationale for decisions.

### Implementation Guidelines
- **Code Edits**: The AI agent must perform all code changes using the edit tools.
- **Command Execution**: The AI agent must run all commands in the chat window context and parse output for errors.
- **Migration Commands**: When creating and running migrations, run commands in the API docker container.
- **Testing Protocol**: Pay particular attention to API testing logic (routes, service, model, tests). Always run tests after making changes.
- **Individual Tests**: Run them in the API docker container using `docker exec api pytest...`
- **Full Test Suite**: Use `make docker-test`
- **Environment Variables**: Assess using `cat .env` - DO NOT create or modify env files.
- **Configuration Values**: Ask user to add or change configuration if needed.
- **Database/Redis Scripts**: Run in API docker container.
- **Container Names**: Always run `docker ps` before creating commands that use container names.
- **Docker Version**: Never use deprecated `docker-compose` - always use `docker compose`.

### Documentation Requirements
- Maintain current patterns, conventions, and configuration at all cost.
- Document specific changes to established patterns.
- Use copious docstrings and comments in source code for context.
- Create markdown documents in documentation directory for significant pattern changes.

## Comprehensive Assessment

### Current Application Architecture
Based on the codebase analysis, this is a full-stack application with:

**Backend (FastAPI)**:
- FastAPI-based REST API with JWT authentication
- SQLAlchemy ORM with PostgreSQL database
- Alembic for database migrations
- Celery workers for background tasks
- Redis for caching and task queue
- Comprehensive logging system
- Docker containerization

**Frontend (React)**:
- React/TypeScript frontend application
- Modern UI components and routing
- Integration with backend API

**Infrastructure**:
- Docker Compose for multi-service orchestration
- Separate configurations for development, testing, and production
- Background services for external API integrations
- Comprehensive testing framework

**Key Services**:
- API service (FastAPI)
- Worker service (Celery)
- Flower service (Celery monitoring)  
- Frontend service (React)
- PostgreSQL database
- Redis cache/queue

### Identified Replacement Scope

The following occurrences of `fastapi-k8-proto` and `fastapi_k8_proto` have been identified:

**1. Service Names and Responses** (7 files):
- `app/api/endpoints/health.py` - Health check response
- `tests/test_health.py` - Test assertion
- `documentaion/LOGGING.md` - Service field in logging config

**2. Database Names** (4 files):
- `docker-compose.prod.yml` - PostgreSQL database name
- `alembic.ini` - Database connection URL
- Background service database connections
- Development script database references

**3. Container Names and Infrastructure** (3 files):
- `reset_and_run_concurrent_campaigns_test.sh` - Container name references
- `test-output-sample.md` - Container names in logs
- Circuit breaker integration tests - Redis host references

**4. Documentation** (6 files):
- All migration guide documentation
- API testing instructions
- README files
- Logging configuration examples

**5. File Paths and Working Directories** (2 files):
- Background service smoke tests
- Path references in test output

## Step-by-Step Replacement Plan

### Phase 1: Infrastructure and Configuration Files

#### Step 1.1: Update Docker Compose Production Configuration
**Goal**: Replace database name in production Docker Compose file

**Actions**:
1. Update `docker-compose.prod.yml`
2. Replace `POSTGRES_DB: fastapi_k8_proto` with `POSTGRES_DB: lead_gen`
3. Replace all environment variable references `POSTGRES_DB=fastapi_k8_proto` with `POSTGRES_DB=lead_gen`

**Files to Modify**:
- `docker-compose.prod.yml`

**Verification Strategy**:
```bash
# Verify the changes
grep -n "lead_gen" docker-compose.prod.yml
grep -n "fastapi_k8_proto" docker-compose.prod.yml  # Should return no results
```

**Expected Result**: All database references use `lead_gen` instead of `fastapi_k8_proto`

---

#### Step 1.2: Update Alembic Configuration
**Goal**: Update database connection URL in Alembic configuration

**Actions**:
1. Update `alembic.ini`
2. Replace `sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/fastapi_k8_proto`
3. With `sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/lead_gen`

**Files to Modify**:
- `alembic.ini`

**Verification Strategy**:
```bash
# Verify the changes
grep -n "lead_gen" alembic.ini
grep -n "fastapi_k8_proto" alembic.ini  # Should return no results
```

**Expected Result**: Alembic points to the correct database name

---

#### Step 1.3: Update Development Scripts
**Goal**: Update database references in development scripts

**Actions**:
1. Update `scripts/docker-dev.sh`
2. Replace `fastapi_k8_proto` with `lead_gen` in PostgreSQL connection

**Files to Modify**:
- `scripts/docker-dev.sh`

**Verification Strategy**:
```bash
# Verify the changes
grep -n "lead_gen" scripts/docker-dev.sh
grep -n "fastapi_k8_proto" scripts/docker-dev.sh  # Should return no results
```

**Expected Result**: Development scripts reference correct database

---

### Phase 2: Application Code and Service Names

#### Step 2.1: Update Health Check Service Name
**Goal**: Update the service name returned by health check endpoint

**Actions**:
1. Update `app/api/endpoints/health.py`
2. Replace `{"status": "healthy", "service": "fastapi-k8-proto"}`
3. With `{"status": "healthy", "service": "lead-gen"}`

**Files to Modify**:
- `app/api/endpoints/health.py`

**Verification Strategy**:
```bash
# Test the health endpoint in Docker
docker exec -it <api-container> curl http://localhost:8000/api/v1/health
```

**Expected Result**: Health endpoint returns `"service": "lead-gen"`

---

#### Step 2.2: Update Health Check Test
**Goal**: Update test assertion to match new service name

**Actions**:
1. Update `tests/test_health.py`
2. Replace `assert response.json() == {"status": "healthy", "service": "fastapi-k8-proto"}`
3. With `assert response.json() == {"status": "healthy", "service": "lead-gen"}`

**Files to Modify**:
- `tests/test_health.py`

**Verification Strategy**:
```bash
# Run the health test
docker exec <api-container> pytest tests/test_health.py -v
```

**Expected Result**: Health test passes with new assertion

---

#### Step 2.3: Update Circuit Breaker Integration Tests
**Goal**: Update Redis host references in integration tests

**Actions**:
1. Update `tests/test_circuit_breaker_integration.py`
2. Replace `redis_host = os.getenv('REDIS_HOST', 'fastapi-k8-proto-redis-1')`
3. With `redis_host = os.getenv('REDIS_HOST', 'lead-gen-redis-1')`

**Files to Modify**:
- `tests/test_circuit_breaker_integration.py`

**Verification Strategy**:
```bash
# Run circuit breaker tests
docker exec <api-container> pytest tests/test_circuit_breaker_integration.py -v
```

**Expected Result**: Circuit breaker tests pass with new container names

---

### Phase 3: Background Services and Database Connections

#### Step 3.1: Update Background Service Database Connections
**Goal**: Update database URLs in background service utilities

**Actions**:
1. Update `app/background_services/smoke_tests/utils/database_utils.py`
2. Replace `db_url = f"postgresql://postgres:postgres@localhost:15432/fastapi_k8_proto"`
3. With `db_url = f"postgresql://postgres:postgres@localhost:15432/lead_gen"`

4. Update `app/background_services/smoke_tests/test_campaign_flow.py`
5. Replace similar database URL reference

**Files to Modify**:
- `app/background_services/smoke_tests/utils/database_utils.py`
- `app/background_services/smoke_tests/test_campaign_flow.py`

**Verification Strategy**:
```bash
# Test database connection in smoke tests
docker exec <api-container> python -c "
from app.background_services.smoke_tests.utils.database_utils import get_db_connection
print('Database connection successful')
"
```

**Expected Result**: Background services connect to correct database

---

### Phase 4: Scripts and Automation

#### Step 4.1: Update Test Automation Script
**Goal**: Update container name references in test automation

**Actions**:
1. Update `reset_and_run_concurrent_campaigns_test.sh`
2. Replace all instances of `fastapi-k8-proto-api-1` with `lead-gen-api-1`
3. Replace all instances of `fastapi-k8-proto-postgres-1` with `lead-gen-postgres-1`
4. Replace all instances of `fastapi-k8-proto-redis-1` with `lead-gen-redis-1`
5. Update grep patterns that search for container names

**Files to Modify**:
- `reset_and_run_concurrent_campaigns_test.sh`

**Verification Strategy**:
```bash
# Check if script can find containers
bash reset_and_run_concurrent_campaigns_test.sh --dry-run
```

**Expected Result**: Script correctly identifies new container names

---

### Phase 5: Documentation Updates

#### Step 5.1: Update Migration Documentation
**Goal**: Update all references in migration documentation

**Actions**:
1. Update `documentaion/api-testing-review-instructions.md`
2. Replace `fastapi-k8-proto application` with `lead-gen application`

3. Update `documentaion/campaign-business-logic-migration.md`
4. Replace `FastAPI application (fastapi-k8-proto)` with `FastAPI application (lead-gen)`

5. Update `documentaion/organization-business-logic-migration.md`
6. Replace `FastAPI-based fastapi-k8-proto application` with `FastAPI-based lead-gen application`

7. Update `documentaion/leads-business-logic-migration.md`
8. Replace `FastAPI application (fastapi-k8-proto)` with `FastAPI application (lead-gen)`

9. Update `documentaion/auth-business-logic-migration.md`
10. Replace `FastAPI application (fastapi-k8-proto)` with `FastAPI application (lead-gen)`

**Files to Modify**:
- `documentaion/api-testing-review-instructions.md`
- `documentaion/campaign-business-logic-migration.md`
- `documentaion/organization-business-logic-migration.md`
- `documentaion/leads-business-logic-migration.md`
- `documentaion/auth-business-logic-migration.md`

**Verification Strategy**:
```bash
# Verify all documentation changes
grep -r "fastapi-k8-proto" documentaion/
grep -r "lead-gen" documentaion/
```

**Expected Result**: Documentation consistently references `lead-gen`

---

#### Step 5.2: Update Testing Documentation
**Goal**: Update testing documentation title and references

**Actions**:
1. Update `documentaion/README_TESTING.md`
2. Replace `# Testing in fastapi-k8-proto` with `# Testing in lead-gen`

**Files to Modify**:
- `documentaion/README_TESTING.md`

**Verification Strategy**:
```bash
# Verify documentation header
head -n 5 documentaion/README_TESTING.md
```

**Expected Result**: Testing documentation reflects new project name

---

#### Step 5.3: Update Logging Configuration Documentation
**Goal**: Update service name in logging configuration examples

**Actions**:
1. Update `documentaion/LOGGING.md`
2. Replace `service: fastapi-k8-proto` with `service: lead-gen`
3. Replace `job: fastapi-k8-proto` with `job: lead-gen`
4. Replace `- job_name: fastapi-k8-proto` with `- job_name: lead-gen`

**Files to Modify**:
- `documentaion/LOGGING.md`

**Verification Strategy**:
```bash
# Verify logging configuration changes
grep -n "lead-gen" documentaion/LOGGING.md
grep -n "fastapi-k8-proto" documentaion/LOGGING.md  # Should return no results
```

**Expected Result**: Logging configuration uses new service name

---

### Phase 6: Sample Output and Test Files

#### Step 6.1: Update Test Output Sample
**Goal**: Update container names in test output documentation

**Actions**:
1. Update `test-output-sample.md`
2. Replace all occurrences of `fastapi-k8-proto-*` container names with `lead-gen-*`
3. Update path references from `/home/ek/dev/fastapi-k8-proto/` to `/home/ek/dev/leadGen/`

**Files to Modify**:
- `test-output-sample.md`

**Verification Strategy**:
```bash
# Verify test output sample changes
grep -c "lead-gen" test-output-sample.md
grep -c "fastapi-k8-proto" test-output-sample.md  # Should be 0
```

**Expected Result**: Test output sample reflects new container names

---

#### Step 6.2: Update Background Service Test Output
**Goal**: Update path references in background service test output

**Actions**:
1. Update `app/background_services/smoke_tests/test ouput prompt.md`
2. Replace path references from `fastapi-k8-proto` to `leadGen`

**Files to Modify**:
- `app/background_services/smoke_tests/test ouput prompt.md`

**Verification Strategy**:
```bash
# Verify path references updated
grep -n "leadGen" "app/background_services/smoke_tests/test ouput prompt.md"
```

**Expected Result**: Background service test output uses correct paths

---

### Phase 7: Comprehensive Verification and Testing

#### Step 7.1: Database Migration Verification
**Goal**: Ensure database changes are properly migrated

**Actions**:
1. Create new Alembic migration if database name changes require it
2. Run migration in API container
3. Verify database connectivity

**Commands to Run**:
```bash
# Check current database status
docker exec <api-container> alembic current

# Create migration if needed (only if schema changes required)
docker exec <api-container> alembic revision --autogenerate -m "Update database name references"

# Apply migrations
docker exec <api-container> alembic upgrade head
```

**Verification Strategy**:
```bash
# Test database connection
docker exec <api-container> python -c "
from app.core.database import SessionLocal
db = SessionLocal()
print('Database connection successful')
db.close()
"
```

**Expected Result**: Database migrations apply successfully

---

#### Step 7.2: Container Name Verification
**Goal**: Verify all container references are updated

**Actions**:
1. Check current running containers
2. Verify scripts can find containers with new names
3. Test container-dependent operations

**Commands to Run**:
```bash
# List current containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# Test container discovery in scripts
grep -r "fastapi-k8-proto" reset_and_run_concurrent_campaigns_test.sh
```

**Verification Strategy**:
```bash
# Verify no old references remain
find . -type f -name "*.py" -o -name "*.sh" -o -name "*.yml" -o -name "*.md" | xargs grep -l "fastapi-k8-proto"
```

**Expected Result**: All container references updated, scripts work correctly

---

#### Step 7.3: Full Application Test Suite
**Goal**: Run comprehensive test suite to ensure no functionality is broken

**Actions**:
1. Run full test suite using make command
2. Run individual API tests
3. Test health endpoints
4. Verify logging output

**Commands to Run**:
```bash
# Run full test suite
make docker-test

# Run health tests specifically
docker exec <api-container> pytest tests/test_health.py -v

# Test health endpoint manually
curl http://localhost:8000/api/v1/health
```

**Verification Strategy**:
- All tests should pass
- Health endpoint should return `"service": "lead-gen"`
- No container connection errors
- Logging should use new service name

**Expected Result**: All tests pass, application functions correctly with new names

---

#### Step 7.4: Background Services Verification
**Goal**: Ensure background services work with updated database connections

**Actions**:
1. Test Celery worker connectivity
2. Verify Redis connections
3. Test background service database operations

**Commands to Run**:
```bash
# Test Celery worker status
docker exec <api-container> celery -A app.workers.celery_app inspect active

# Test Redis connectivity
docker exec <redis-container> redis-cli ping

# Test background service database connection
docker exec <api-container> python -c "
from app.background_services.smoke_tests.utils.database_utils import *
print('Background services database connection successful')
"
```

**Verification Strategy**:
- Celery workers should be active
- Redis should respond with PONG
- Background services should connect to database successfully

**Expected Result**: All background services operational with new configuration

---

### Phase 8: Final Verification and Documentation

#### Step 8.1: Comprehensive Search Verification
**Goal**: Ensure no instances of old project name remain

**Actions**:
1. Perform comprehensive search across entire codebase
2. Check for any missed references
3. Verify case variations

**Commands to Run**:
```bash
# Search for any remaining fastapi-k8-proto references
find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.sh" -o -name "*.ini" -o -name "*.json" \) | xargs grep -l "fastapi-k8-proto"

# Search for underscore variations
find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.sh" -o -name "*.ini" -o -name "*.json" \) | xargs grep -l "fastapi_k8_proto"

# Search for case variations
find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.sh" -o -name "*.ini" -o -name "*.json" \) | xargs grep -i "fastapi.*k8.*proto"
```

**Verification Strategy**:
- No files should contain old project name references
- All searches should return empty results

**Expected Result**: Complete removal of old project name references

---

#### Step 8.2: Application Startup and Smoke Test
**Goal**: Verify entire application starts and functions correctly

**Actions**:
1. Stop all containers
2. Rebuild containers with new configuration
3. Start full application stack
4. Run smoke tests

**Commands to Run**:
```bash
# Stop and clean up
docker compose down -v

# Rebuild and start
docker compose up -d --build

# Wait for services to be healthy
sleep 30

# Run smoke test
curl http://localhost:8000/api/v1/health
curl http://localhost:5173  # Frontend
curl http://localhost:5555  # Flower
```

**Verification Strategy**:
- All services should start successfully
- Health endpoints should respond correctly
- No container errors in logs
- Frontend should load
- Flower monitoring should be accessible

**Expected Result**: Full application stack operational with new project name

---

#### Step 8.3: Create Migration Summary Documentation
**Goal**: Document all changes made during the replacement

**Actions**:
1. Create comprehensive summary of changes
2. Document any issues encountered
3. Update any architectural documentation affected

**Files to Create**:
- `documentaion/project-name-migration-summary.md`

**Content Structure**:
```markdown
# Project Name Migration Summary

## Changes Made
- List of all files modified
- Specific changes in each file
- Database schema changes (if any)

## Container Name Changes
- Old vs new container names
- Impact on scripts and automation

## Verification Results
- Test results
- Performance impact (if any)
- Any issues encountered

## Post-Migration Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Scripts functional
- [ ] No old references remaining
```

**Expected Result**: Complete documentation of migration process

---

## Risk Assessment and Mitigation

### High-Risk Areas
1. **Database Name Changes**: Could break existing data connections
   - **Mitigation**: Test all database connections thoroughly
   - **Rollback**: Keep backup of original configuration files

2. **Container Name Dependencies**: Scripts and automation may fail
   - **Mitigation**: Update all container name references
   - **Rollback**: Revert container names if issues arise

3. **Service Discovery**: Internal service communication may break
   - **Mitigation**: Test all inter-service communication
   - **Rollback**: Keep original service names as fallback

### Medium-Risk Areas
1. **Documentation Consistency**: Mixed naming could cause confusion
   - **Mitigation**: Comprehensive documentation update
   - **Rollback**: Easy to revert documentation changes

2. **External Dependencies**: Third-party integrations might be affected
   - **Mitigation**: Test all external API integrations
   - **Rollback**: Isolated changes, easy to revert

### Low-Risk Areas
1. **Test Files**: Changes are isolated and testable
   - **Mitigation**: Run full test suite
   - **Rollback**: Simple to revert test changes

## Success Criteria

### Primary Success Metrics
- [ ] All occurrences of `fastapi-k8-proto` replaced with `lead-gen`
- [ ] All occurrences of `fastapi_k8_proto` replaced with `lead_gen`
- [ ] All tests passing
- [ ] Application starts successfully
- [ ] All services accessible

### Secondary Success Metrics
- [ ] Documentation consistency maintained
- [ ] No performance degradation
- [ ] All automation scripts functional
- [ ] Background services operational
- [ ] Logging maintains proper format

### Completion Verification
- [ ] Comprehensive search returns no old references
- [ ] Full test suite passes
- [ ] Application smoke test successful
- [ ] All container operations functional
- [ ] Documentation updated and consistent

## Emergency Rollback Plan

If issues arise during migration:

1. **Immediate Actions**:
   ```bash
   # Stop current containers
   docker compose down
   
   # Restore original files from git
   git checkout HEAD -- .
   
   # Restart with original configuration
   docker compose up -d
   ```

2. **Selective Rollback**:
   - Revert specific files causing issues
   - Test incrementally
   - Resume migration from stable point

3. **Complete Rollback**:
   - Restore all original file contents
   - Verify application functionality
   - Document issues for future resolution

## Post-Migration Validation

After completing all steps:

1. **Functional Validation**:
   - All API endpoints respond correctly
   - Database operations successful
   - Worker tasks execute properly
   - Frontend loads and functions

2. **Integration Validation**:
   - Service-to-service communication
   - External API integrations
   - Authentication and authorization
   - Logging and monitoring

3. **Performance Validation**:
   - Response times unchanged
   - Resource utilization normal
   - No memory leaks or connection issues

This comprehensive plan ensures a systematic, safe, and verifiable replacement of all project name references while maintaining application functionality and architectural integrity. 