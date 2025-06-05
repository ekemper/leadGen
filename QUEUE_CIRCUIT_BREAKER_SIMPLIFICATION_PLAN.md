# Queue and Circuit Breaker Simplification Implementation Plan

## Executive Summary

This plan implements a comprehensive simplification of the queue/circuit breaker system by:
- **Removing campaign paused state** - campaigns will only have CREATED, RUNNING, COMPLETED, FAILED states
- **Simplifying circuit breaker** - only OPEN and CLOSED states (removing HALF_OPEN)
- **Job-level state management** - jobs maintain paused state, campaigns remain RUNNING
- **Manual-only resume** - only frontend can close circuit breaker and resume operations
- **Removing unavailable_services complexity** - circuit breaker state is single source of truth

**🎯 Development Environment**: Since we're in development and all campaigns will be deleted during testing, this plan skips complex data migration procedures and focuses on clean implementation.

## Current Architecture Analysis

### Current Complexity Issues
1. **Campaign paused state** complicates state machine with automatic resume logic
2. **unavailable_services** concept duplicates circuit breaker state tracking
3. **HALF_OPEN circuit breaker state** adds unnecessary complexity
4. **Multiple pause/resume triggers** create race conditions and unpredictable behavior
5. **Service-specific dependency tracking** over-complicates job routing decisions

### Current Patterns to Maintain
- **API JSON response format**: `{"status": "success", "data": {...}}`
- **Docker container execution**: Tests run in `leadgen-api-1` container
- **Database verification**: Tests check actual DB state after API calls
- **Migration pattern**: Use `flask db migrate` and `flask db upgrade`
- **Logging pattern**: Structured logging with context and error tracking

## Simplified Business Rules

### Circuit Breaker Rules
1. **Only two states**: OPEN (service down) and CLOSED (service working)
2. **Any service error** → circuit breaker opens immediately
3. **Frontend manual action only** → circuit breaker closes
4. **Single global state** → there is only one global breaker state ( not based on services )

### Job State Management
1. **Breaker opens** → all PENDING/RUNNING jobs → PAUSED
2. **Breaker closes** → all PAUSED jobs → PENDING + new celery tasks created
3. **Jobs maintain pause reason** for troubleshooting
4. **No service-specific job filtering** → all jobs affected equally

### Campaign State Management  
1. **Campaigns never pause** → remain in RUNNING state even when breaker opens
2. **Job pause ≠ campaign pause** → campaigns track overall progress, not individual failures
3. **Campaign completion** → based on all jobs completed/failed, not pause state

## Implementation Plan

### Phase 1: Test Foundation and Risk Assessment (Steps 1-3)

#### Step 1: Create Comprehensive Test Suite for New Logic
**Goal**: Establish test coverage for simplified system before making changes
**Actions**:
- Create `tests/test_simplified_circuit_breaker.py` with:
  - Circuit breaker open/close only (no half-open)
  - Job pause/resume on breaker state changes
  - Campaign state isolation (no pause state)
  - Manual frontend-only breaker closing
- Create `tests/test_simplified_job_management.py` with:
  - Job pause when breaker opens
  - Job resume when breaker closes (with new celery tasks)
  - Job state transitions without campaign coupling
- Update existing test expectations in:
  - `tests/test_campaign_status_refactor.py`
  - `tests/test_queue_management_api.py`
  - `tests/test_circuit_breaker_integration.py`

**Success Criteria**: 
- All new tests pass with current system (where applicable)
- Test coverage for all simplified business rules
- Clear test failure patterns where simplification changes behavior

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_simplified_circuit_breaker.py -v
docker exec leadgen-api-1 pytest tests/test_simplified_job_management.py -v
```

#### Step 2: Document Technical Risks and Discontinuities
**Goal**: Identify and document all technical risks before proceeding
**Actions**:
- Analyze current campaign/job state dependencies
- Identify potential data consistency issues during transition
- Document rollback procedures for each step
- Create risk mitigation strategies for development deployment
- Document breaking changes to API contracts

**Success Criteria**: 
- Comprehensive risk assessment document created
- Rollback procedures documented for each phase
- Breaking changes clearly identified with mitigation plans

#### Step 3: Clean Development Environment Setup
**Goal**: Prepare clean development environment for simplified implementation
**Actions**:
- Delete all existing campaigns and jobs from development database
- Clear Redis circuit breaker state
- Reset any cached or persistent state related to old logic
- Verify clean slate for implementation

**Success Criteria**: 
- Development database cleared of campaigns and jobs
- Redis state cleared
- Clean environment ready for new implementation

**Validation Strategy**:
```bash
# Clear development data
docker exec leadgen-api-1 python -c "
from app.core.database import SessionLocal
from app.models.campaign import Campaign
from app.models.job import Job
db = SessionLocal()
db.query(Job).delete()
db.query(Campaign).delete()
db.commit()
print('Development data cleared')
"

# Clear Redis state
docker exec leadgen-redis-1 redis-cli FLUSHDB
```

### Phase 2: Circuit Breaker Simplification (Steps 4-8)

#### Step 4: Remove HALF_OPEN State from Circuit Breaker
**Goal**: Simplify circuit breaker to only OPEN/CLOSED states
**Actions**:
- Update `app/core/circuit_breaker.py`:
  - Remove `CircuitState.HALF_OPEN` enum value
  - Remove half-open transition logic in `get_circuit_state()`
  - Remove half-open handling in `record_success()`
  - Simplify `should_allow_request()` to only check OPEN/CLOSED
- Update `app/core/campaign_event_handler.py`:
  - Remove `handle_circuit_breaker_half_open()` method
- Update all tests to remove half-open expectations

**Success Criteria**: 
- Circuit breaker only operates in OPEN/CLOSED states
- No references to HALF_OPEN in codebase
- All circuit breaker tests pass

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_circuit_breaker_integration.py -v
grep -r "HALF_OPEN" app/ # Should return no results
```

#### Step 5: Simplify Circuit Breaker Trigger Logic
**Goal**: Any service error immediately opens circuit breaker
**Actions**:
- Update `CircuitBreakerService.record_failure()`:
  - Remove failure threshold logic
  - Remove sliding window tracking
  - Any failure immediately opens circuit breaker
- Update circuit breaker state management:
  - Remove service-specific state tracking
  - Implement global circuit breaker state
- Update error handling in service integrations to trigger immediate breaker opening

**Success Criteria**:
- Any service failure immediately opens global circuit breaker
- No complex failure counting or windowing logic
- Single global circuit breaker state

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_simplified_circuit_breaker.py::test_immediate_open_on_failure -v
```

#### Step 6: Implement Manual-Only Circuit Breaker Closing
**Goal**: Only frontend API calls can close circuit breaker
**Actions**:
- Create new API endpoint `POST /api/v1/queue-management/circuit-breaker/close`:
  - Closes global circuit breaker
  - Triggers job resume process
  - Returns success/failure with detailed status
- Remove all automatic circuit breaker closing logic
- Update `CircuitBreakerService` to only close on manual command
- Add proper authorization checks for circuit breaker control

**Success Criteria**:
- Circuit breaker only closes via API endpoint
- No automatic closing logic remains
- Proper authorization for circuit breaker control

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_queue_management_api.py::test_manual_circuit_breaker_close -v
curl -X POST http://localhost:8000/api/v1/queue-management/circuit-breaker/close -H "Authorization: Bearer $TOKEN"
```

#### Step 7: Remove Service-Specific Circuit Breaker Logic
**Goal**: Replace service-specific states with single global circuit breaker
**Actions**:
- Update `CircuitBreakerService` to manage single global state instead of per-service states
- Remove `ThirdPartyService` enum usage in circuit breaker state management
- Update Redis keys to use global circuit breaker state
- Simplify `should_allow_request()` to check global state only
- Update all service integrations to use global circuit breaker

**Success Criteria**:
- Single global circuit breaker state in Redis
- No service-specific circuit breaker tracking
- All services check same global circuit breaker state

**Validation Strategy**:
```bash
docker exec leadgen-api-1 python -c "
from app.core.circuit_breaker import get_circuit_breaker
cb = get_circuit_breaker()
print('Global state:', cb.get_global_state())
"
```

#### Step 8: Update Queue Management API for Simplified Circuit Breaker
**Goal**: Align queue management endpoints with simplified circuit breaker
**Actions**:
- Update `app/api/endpoints/queue_management.py`:
  - Modify circuit breaker status endpoint to return global state
  - Update pause/resume endpoints to work with global circuit breaker
  - Remove service-specific circuit breaker endpoints
- Update API response schemas to reflect simplified structure
- Update error handling for simplified circuit breaker operations

**Success Criteria**:
- Queue management API reflects simplified circuit breaker
- Consistent API responses for global circuit breaker state
- No service-specific circuit breaker endpoints

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_queue_management_api.py -v
curl http://localhost:8000/api/v1/queue-management/circuit-breakers
```

### Phase 3: Job State Management Simplification (Steps 9-13)

#### Step 9: Implement Job Pause on Circuit Breaker Open
**Goal**: All PENDING/RUNNING jobs pause when circuit breaker opens
**Actions**:
- Update `app/core/queue_manager.py`:
  - Remove service-specific job filtering logic
  - Implement `pause_all_jobs_on_breaker_open()` method
  - Update `should_process_job()` to check global circuit breaker only
- Create job pause cascade when circuit breaker opens:
  - Pause all PENDING jobs → JobStatus.PAUSED
  - Pause all RUNNING jobs → JobStatus.PAUSED (with graceful handling)
- Update job error messages to include circuit breaker context

**Success Criteria**:
- All jobs pause when circuit breaker opens
- No service-specific job filtering


**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_simplified_job_management.py::test_all_jobs_pause_on_breaker_open -v
```

#### Step 10: Implement Job Resume on Circuit Breaker Close
**Goal**: All PAUSED jobs resume as PENDING with new celery tasks when circuit breaker closes
**Actions**:
- Update `app/core/queue_manager.py`:
  - Implement `resume_all_jobs_on_breaker_close()` method
  - Set PAUSED jobs → PENDING status
  - Create new celery tasks for each resumed job
- Update job task creation logic:
  - Generate new task IDs for resumed jobs
  - Preserve job data and context
  - Handle job priority and queue assignment
- Add comprehensive error handling for job resume failures

**Success Criteria**:
- All paused jobs resume when circuit breaker closes
- New celery tasks created for resumed jobs
- Proper error handling for resume failures

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_simplified_job_management.py::test_all_jobs_resume_on_breaker_close -v
```

#### Step 11: Remove Service-Specific Job Dependencies
**Goal**: Jobs no longer depend on specific service availability
**Actions**:
- Update `app/models/job.py`:
  - Remove service dependency tracking
  - Simplify job type logic to only check global circuit breaker
- Update `app/workers/campaign_tasks.py`:
  - Remove service-specific job routing
  - Simplify job processing to check global circuit breaker only
- Update job creation logic to remove service dependency calculations

**Success Criteria**:
- Jobs only check global circuit breaker state
- No service-specific job dependency logic
- Simplified job routing and processing

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_simplified_job_management.py::test_no_service_specific_dependencies -v
grep -r "job.*service.*dependency" app/ # Should return minimal results
```

#### Step 12: Update Job Status API Endpoints
**Goal**: Job status endpoints reflect simplified job management
**Actions**:
- Update `app/api/endpoints/jobs.py`:
  - Remove service-specific job filtering
  - Update job status responses to include circuit breaker context
  - Simplify job pause/resume endpoints
- Update job status schemas to reflect simplified structure
- Remove deprecated job management endpoints

**Success Criteria**:
- Job status APIs reflect simplified job management
- Consistent API responses for job status
- No service-specific job filtering in APIs

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_jobs_api.py -v
curl http://localhost:8000/api/v1/jobs/status
```

#### Step 13: Create Job Resume Task Creation Logic
**Goal**: Reliable celery task creation for resumed jobs
**Actions**:
- Create `app/services/job_resume_service.py`:
  - Handle bulk job resume with celery task creation
  - Implement retry logic for failed task creation
  - Provide detailed resume status reporting
- Update celery task definitions to handle resumed job context
- Add comprehensive logging for job resume operations

**Success Criteria**:
- Reliable celery task creation for resumed jobs
- Comprehensive error handling and retry logic
- Detailed logging and monitoring for job resume

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_job_resume_service.py -v
```

### Phase 4: Campaign State Simplification (Steps 14-18)

#### Step 14: Remove Campaign PAUSED State
**Goal**: Campaigns only have CREATED, RUNNING, COMPLETED, FAILED states
**Actions**:
- Update `app/models/campaign_status.py`:
  - Remove `CampaignStatus.PAUSED` enum value
  - Update campaign status validation logic
- Create database migration to remove PAUSED state from enum:
  - Simple enum update since no existing data needs preservation
- Update campaign state machine validation

**Success Criteria**:
- No PAUSED state in campaign status enum
- Database migration removes PAUSED state
- Campaign state validation updated

**Validation Strategy**:
```bash
docker exec leadgen-api-1 flask db migrate -m "Remove campaign paused state"
docker exec leadgen-api-1 flask db upgrade
docker exec leadgen-api-1 pytest tests/test_campaign_status.py -v
```

#### Step 15: Update Campaign Status Logic
**Goal**: Campaigns remain RUNNING when circuit breaker opens
**Actions**:
- Update `app/models/campaign.py`:
  - Remove `pause()` and `resume()` methods
  - Update `can_be_started()` to only check global circuit breaker
  - Simplify campaign state transitions
- Update `app/services/campaign_status_monitor.py`:
  - Remove automatic campaign pausing logic
  - Focus on job status monitoring only
- Remove campaign pause/resume from circuit breaker event handling

**Success Criteria**:
- Campaigns never automatically pause
- Campaign state logic simplified
- Campaign status monitoring focuses on job tracking only

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_campaign_status.py::test_no_automatic_pause -v
```

#### Step 16: Remove Campaign Event Handler Complexity
**Goal**: Simplify or remove campaign event handler entirely
**Actions**:
- Evaluate `app/core/campaign_event_handler.py` for deprecation:
  - Remove automatic campaign pausing logic
  - Keep minimal event logging if needed
  - Consider complete removal per TODO comment
- Update circuit breaker to remove campaign event handler integration
- Move any necessary functionality to job-level event handling

**Success Criteria**:
- Campaign event handler simplified or removed
- No automatic campaign state changes from circuit breaker events
- Event logging maintained for monitoring

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_campaign_events.py -v
grep -r "CampaignEventHandler" app/ # Minimal or no results
```

#### Step 17: Update Campaign API Endpoints
**Goal**: Campaign APIs reflect simplified state management
**Actions**:
- Update `app/api/endpoints/campaigns.py`:
  - Remove campaign pause/resume endpoints
  - Update campaign status responses
  - Simplify campaign start validation logic
- Update campaign schemas to remove paused state references
- Remove deprecated campaign management endpoints

**Success Criteria**:
- Campaign APIs reflect simplified state management
- No campaign pause/resume endpoints
- Simplified campaign validation logic

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_campaigns_api.py -v
curl http://localhost:8000/api/v1/campaigns/status
```

#### Step 18: Remove unavailable_services Logic
**Goal**: Replace unavailable_services with circuit breaker state checks
**Actions**:
- Update `app/services/campaign.py`:
  - Remove `unavailable_services` tracking
  - Replace with global circuit breaker state checks
  - Simplify campaign start validation
- Update all service integrations to remove unavailable_services usage
- Remove unavailable_services from API responses and schemas

**Success Criteria**:
- No unavailable_services tracking in codebase
- All service availability checked via circuit breaker state
- Simplified campaign and job validation logic

**Validation Strategy**:
```bash
grep -r "unavailable_services" app/ # Should return no results
docker exec leadgen-api-1 pytest tests/test_campaign_service.py -v
```

### Phase 5: Integration and Testing (Steps 19-23)

#### Step 19: Update All Service Integrations
**Goal**: All third-party service integrations use simplified circuit breaker
**Actions**:
- Update all service clients in `app/services/`:
  - Apollo service integration
  - OpenAI service integration  
  - Instantly service integration
  - MillionVerifier service integration
  - Perplexity service integration
- Ensure all services trigger global circuit breaker on errors
- Remove service-specific error handling complexity

**Success Criteria**:
- All services use global circuit breaker
- Consistent error handling across all services
- No service-specific circuit breaker logic

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_service_integrations.py -v
```

#### Step 20: Update Frontend Queue Management Interface
**Goal**: Frontend only controls circuit breaker closing (note: defer detailed frontend changes per requirements)
**Actions**:
- Document required frontend changes in `FRONTEND_QUEUE_MANAGEMENT_CHANGES.md`:
  - Remove service-specific controls
  - Add global circuit breaker close button
  - Simplify queue status display
- Update API contracts for frontend integration
- Ensure backend APIs support simplified frontend requirements

**Success Criteria**:
- Backend APIs ready for simplified frontend
- Clear documentation for frontend changes
- API contracts defined for new queue management

**Validation Strategy**:
```bash
# Test API endpoints that frontend will use
curl http://localhost:8000/api/v1/queue-management/status
curl -X POST http://localhost:8000/api/v1/queue-management/circuit-breaker/close
```

#### Step 21: Run Comprehensive Test Suite
**Goal**: Ensure all changes work together correctly
**Actions**:
- Run full test suite with new logic:
  - All circuit breaker tests
  - All job management tests
  - All campaign tests
  - All queue management tests
- Fix any integration issues discovered
- Update test assertions to match new behavior

**Success Criteria**:
- All tests pass with new simplified logic
- No breaking integration issues
- Test coverage maintained or improved

**Validation Strategy**:
```bash
make docker-test
docker exec leadgen-api-1 pytest tests/ -v --tb=short
```

#### Step 22: Performance and Load Testing
**Goal**: Ensure simplified system performs well under load
**Actions**:
- Run existing smoke tests with new logic
- Test circuit breaker performance with job pause/resume
- Monitor system performance during state transitions
- Test with multiple concurrent campaigns and jobs

**Success Criteria**:
- System performance maintained or improved
- No performance regressions in state transitions
- Smoke tests pass with new logic

**Validation Strategy**:
```bash
# Run smoke tests
python app/background_services/smoke_tests/test_concurrent_campaigns_flow.py
```

#### Step 23: Update Documentation and Remove TODOs
**Goal**: Complete documentation updates and clean up TODOs
**Actions**:
- Update all docstrings to reflect new simplified logic
- Update `README.md` files with new system behavior
- Create `QUEUE_CIRCUIT_BREAKER_ARCHITECTURE.md` documenting new patterns
- Remove all TODOs addressed by this implementation
- Update API documentation with new endpoints and schemas

**Success Criteria**:
- All documentation updated
- All relevant TODOs removed from codebase
- Clear architectural documentation for new patterns

**Validation Strategy**:
```bash
grep -r "TODO" app/ # Should return minimal results
```

## Post-Implementation: Update Concurrent Campaign Flow Test

### Step 24: Update test_concurrent_campaigns_flow.py for New Logic
**Goal**: Update the concurrent campaign flow test to work with simplified circuit breaker logic
**Actions**:
- Update `app/background_services/smoke_tests/test_concurrent_campaigns_flow.py`:
  - Replace campaign status polling with circuit breaker state polling
  - Update `wait_for_campaign_pause_propagation()` to `wait_for_circuit_breaker_open()`
  - Modify test logic to expect campaigns to remain RUNNING when circuit breaker opens
  - Update test assertions to check job pause status instead of campaign pause status
  - Simplify circuit breaker state checking to use global state only
- Update related utility functions in `app/background_services/smoke_tests/utils/`:
  - `circuit_breaker_utils.py`: Update to work with global circuit breaker state
  - `job_utils.py`: Update monitoring to focus on job state rather than campaign state
- Remove campaign-specific pause/resume logic from smoke tests

**Rationale**: 
With the new simplified logic:
- **Campaigns never pause** → they remain RUNNING even when circuit breaker opens
- **Circuit breaker state** → is the single source of truth for system health
- **Job state** → is what actually pauses/resumes based on circuit breaker
- **Test continuation logic** → should be based on circuit breaker state, not campaign status

**Success Criteria**:
- Smoke test polls circuit breaker state instead of campaign status
- Test correctly identifies when to continue based on global circuit breaker state
- Test assertions updated to expect campaigns to remain RUNNING
- Job state monitoring replaces campaign state monitoring
- Test passes with new simplified logic

**Validation Strategy**:
```bash
# Run the updated smoke test
python app/background_services/smoke_tests/test_concurrent_campaigns_flow.py

# Verify test logic with circuit breaker state changes
docker exec leadgen-api-1 python -c "
from app.core.circuit_breaker import get_circuit_breaker
from app.core.logger import get_logger
logger = get_logger(__name__)

# Test circuit breaker state polling
cb = get_circuit_breaker()
state = cb.get_global_state()
logger.info(f'Global circuit breaker state: {state}')
print(f'Circuit breaker state: {state}')
"
```

**Key Changes Required**:

1. **Replace campaign status polling**:
```python
# OLD: Wait for campaigns to pause
def wait_for_campaign_pause_propagation(token, campaign_ids, api_base, timeout_seconds=30):
    # Wait for campaigns to change to PAUSED status
    
# NEW: Wait for circuit breaker to open
def wait_for_circuit_breaker_open(token, api_base, timeout_seconds=30):
    # Poll circuit breaker state until OPEN
```

2. **Update test continuation logic**:
```python
# OLD: Check if campaigns are paused to determine test continuation
if campaigns_paused:
    return "stop_test", "Campaigns paused due to service issues"

# NEW: Check circuit breaker state to determine test continuation  
if circuit_breaker_open:
    return "stop_test", "Circuit breaker open due to service issues"
```

3. **Simplify circuit breaker state checking**:
```python
# OLD: Check multiple service-specific circuit breakers
for service, status in circuit_breakers.items():
    if status.get("circuit_state") == "open":
        open_breakers.append(service)

# NEW: Check single global circuit breaker state
circuit_breaker_open = queue_status["data"]["circuit_breaker"]["state"] == "open"
```

4. **Update assertions to expect running campaigns**:
```python
# OLD: Expect campaigns to pause when circuit breaker opens
assert campaign_status == "PAUSED", "Campaign should be paused when circuit breaker opens"

# NEW: Expect campaigns to remain running when circuit breaker opens
assert campaign_status == "RUNNING", "Campaign should remain running when circuit breaker opens"
assert jobs_paused > 0, "Jobs should be paused when circuit breaker opens"
```

This update ensures the smoke test works correctly with the new simplified logic where circuit breaker state is the single source of truth for system health, and campaigns never pause regardless of circuit breaker state.

## Technical Risk Assessment

### High-Risk Areas

1. **Job State Consistency Risk**
   - **Risk**: Jobs may be left in inconsistent states during circuit breaker transitions
   - **Mitigation**: Atomic job state updates with database transactions
   - **Rollback**: Database transaction rollback on any job state update failure

2. **Celery Task Creation Risk**
   - **Risk**: Resumed jobs may fail to create new celery tasks
   - **Mitigation**: Comprehensive retry logic and error handling for task creation
   - **Rollback**: Mark jobs as failed if task creation fails, maintain manual retry capability

### Medium-Risk Areas

3. **API Contract Breaking Changes**
   - **Risk**: Frontend or API clients may break with new simplified responses
   - **Mitigation**: Maintain backward compatibility where possible, clear breaking change documentation. The updates to the front end will be performed Subsequently. just document the needed front end changes based on the refactoring of the endpoints.

4. **Circuit Breaker Race Conditions**
   - **Risk**: Concurrent requests during circuit breaker state changes may cause inconsistencies
   - **Mitigation**: Redis-based locking for circuit breaker state changes
   - **Rollback**: Circuit breaker state can be manually reset via API

## Success Criteria

### Technical Success Criteria
- [ ] Circuit breaker only has OPEN/CLOSED states
- [ ] Jobs pause/resume based on global circuit breaker state
- [ ] Campaigns never enter PAUSED state
- [ ] All service integrations use global circuit breaker
- [ ] Frontend can manually close circuit breaker only
- [ ] All tests pass with new logic
- [ ] No unavailable_services logic remains
- [ ] All TODOs addressed and removed

### Business Success Criteria
- [ ] System behavior is predictable and simple to understand
- [ ] Manual control over system resume operations
- [ ] Clear visibility into circuit breaker state
- [ ] Reliable job recovery after service issues
- [ ] Maintained system performance under load

## Rollback Procedures

### Database Rollback
```bash
# Rollback specific migration
docker exec leadgen-api-1 flask db downgrade <revision_id>

# Or recreate clean development database
docker exec leadgen-api-1 flask db downgrade base
docker exec leadgen-api-1 flask db upgrade
```

### Code Rollback
```bash
# Revert to previous commit
git revert <commit_hash>

# Or checkout previous working branch
git checkout <previous_branch>
```

### Configuration Rollback
```bash
# Clear Redis circuit breaker state
docker exec leadgen-redis-1 redis-cli FLUSHDB

# Restart services to reset state
docker compose restart
```

## TODO Checklist

All TODOs identified in the codebase that will be addressed by this plan:

### Circuit Breaker TODOs
- [ ] Remove `#TODO: simplify the circuit breaker to not be responsible for the state of individual services. It should only have open and closed states.` (app/core/circuit_breaker.py:23)
- [ ] Remove `#TODO: setting the circuit state should only occur from two specific events: 1) an error from any of the third party api integrations, or an api  call from the front end to close the breaker to resume service` (app/core/circuit_breaker.py:82)  
- [ ] Remove `#TODO we need to remove the concept of half open state. it is not needed. only open and closed states are needed.` (app/core/circuit_breaker.py:104)

### Campaign Event Handler TODOs
- [ ] Remove `# TODO: COMPLETELY REMOVE THIS DEPRICATED CLASS. all pauseing will be at the job level` (app/core/campaign_event_handler.py:21)
- [ ] Remove `#TODO: refactor how we handle the manual resume of the queue. the state of the campaign should only be created, running, or completed` (app/core/campaign_event_handler.py:97)
- [ ] Remove `#TODO: nothing should have to happen to the campaign when the breaker is manually closed , no state change will be needed. It will be the jobs that will be updated to a pending state and resumed with new celery task instantiation` (app/core/campaign_event_handler.py:98)
- [ ] Remove `#TODO: completely remove the concept of a half open breaker` (app/core/campaign_event_handler.py:136)
- [ ] Remove `# TODO this will likely be deprecated because we wont need to pause campaigns` (app/core/campaign_event_handler.py:163)
- [ ] Remove `# TODO: we will want to know why the queue has been stopped but we wont keep the paused state on the campaigns anymore` (app/core/campaign_event_handler.py:191)
- [ ] Remove `# TODO the reason for the breaker triggering will be stored on the breaker class` (app/core/campaign_event_handler.py:192)

### Campaign Service TODOs
- [ ] Remove `# TODO: the circuit breaker states should be independent of the service states, any of the api integrations can trigger  the circuit breaker to open.` (app/services/campaign.py:190)
- [ ] Remove `#TODO: we should not have to check the services. just the open or closed state of the circuit breaker. the state of the circuit breaker is the source of truth` (app/services/campaign.py:194)
- [ ] Remove `#TODO: remove this, we dont need to know which service is available.` (app/services/campaign.py:213)
- [ ] Remove `#TODO: create a helper for this logic, this method id pretty big.` (app/services/campaign.py:227)
- [ ] Remove `#TODO: the state of the circuit breaker should be the source of truth for the conditional to create the instantly lead . not unavailable services` (app/services/campaign.py:228)
- [ ] Remove `#TODO: remove paused state from campaign, refactor states that are possible for campaigns to be created, running, completed.` (app/services/campaign.py:926)
- [ ] Remove `#TODO : remove logic around available services, the open or closed state of the circuit breaker is the source of truth for if a campaign can be started` (app/services/campaign.py:934)
- [ ] Remove `#TODO: this methos is likely redundant. should be able to just get the state of the circuit breaker instead of checking the services.` (app/services/campaign.py:964)
- [ ] Remove `# TODO: this method is likely redundant. should be able to just get the state of the circuit breaker instead of checking the services.` (app/services/campaign.py:1006)

### Campaign Status TODOs
- [ ] Remove `# TODO: the paused status of the campaign should be removed` (app/models/campaign_status.py:2)

### Job Status Handler TODOs
- [ ] Remove `# TODO: Remove this - campaigns will no longer have a paused state` (app/services/job_status_handler.py:105)
- [ ] Remove `#TODO : this should only have to be evaluated if the job failure was something other than a third party api failure which will be handled by the circuit breaker logic` (app/services/job_status_handler.py:157)
- [ ] Remove `# TODO: Depricated` (app/services/job_status_handler.py:211)
- [ ] Remove `# TODO; this class may be entirely Depricated` (app/services/job_status_handler.py:291)

### Queue Manager TODOs
- [ ] Remove `# TODO : this logic needs to be simplified - the open or closed state of the circuit breaker is the only source of truth needed for determining if a job can be run` (app/core/queue_manager.py:37)
- [ ] Remove `# TODO we can remove the dependencies on the job types, only the breaker matters, not which services are needed for which type of job` (app/core/queue_manager.py:39)
- [ ] Remove `# TODO: this should be depricated - for pausing jobs, we will pause all of the jobs in a pending or running state regardless of what services that job depends on. please siimplify` (app/core/queue_manager.py:68)
- [ ] Remove `# TODO: this should be depricated - for resuming jobs, we will put all of the jobs in a paused state back into a pending state regardless of what services that job depends on. please siimplify` (app/core/queue_manager.py:120)
- [ ] Remove `# TODO : simplify to just get paused jobs.` (app/core/queue_manager.py:158)
- [ ] Remove `# TODO: utilize the relation between jobs and leads to gather the relevant info from the database` (app/core/queue_manager.py:187)
- [ ] Remove `# TODO: depricated - we dont care about the per-service pausing of jobs` (app/core/queue_manager.py:235)

### API Endpoint TODOs
- [ ] Remove `# TODO: these campaign related schemas will have to be consolidated.` (app/api/endpoints/queue_management.py:35)
- [ ] Remove `#TODO : the cancel job post endpoint is redundant - please refactor usages of this endpoin to use the delete endpoint instead` (app/api/endpoints/jobs.py:168)

### Other TODOs
- [ ] Remove `# TODO: Add database and Redis connectivity checks` (app/api/endpoints/health.py:10)
- [ ] Remove `# TODO : even with the stubbed out call to millionverifier lets bring the rate limiting back so it can be tested` (app/background_services/email_verifier_service.py:67)
- [ ] Remove `# TODO: Implement actual lead processing logic` (app/workers/campaign_tasks.py:682)
- [ ] Remove `processed_count = 0  # TODO: Replace with actual processing count` (app/workers/campaign_tasks.py:707)

### Test TODOs
- [ ] Remove `# TODO: In actual implementation, this should trigger campaign evaluation` (tests/test_job_status_integration.py:138)
- [ ] Remove `# TODO: Replace with actual service integration` (tests/test_job_status_integration.py:623)
- [ ] Remove `# TODO: This will need service integration - for now simulate the trigger` (tests/test_campaign_status_refactor.py:146)

### Documentation TODOs
- [ ] Remove or complete `documentaion/TODO: Campaign Status Monitoring Implementation.md`

## General Implementation Rules

### Code Quality Standards
- **Complete working code only** - no placeholders or pseudo-code
- **Production-ready quality** - comprehensive error handling and logging
- **Maintain existing patterns** - follow established API response formats and conventions
- **Comprehensive testing** - test-driven development approach with immediate test validation
- **Documentation updates** - update docstrings and comments for all changes

### Technical Guidelines
- **Always question and validate** - challenge any unclear requirements or decisions
- **Ask for clarification** - when implementation details are ambiguous
- **Never make assumptions** - provide rationale for all decisions
- **Run tests immediately** - after each code change, validate with tests
- **Use Docker containers** - run commands in `leadgen-api-1` container for consistency
- **Follow migration patterns** - use `flask db migrate` and `flask db upgrade`
- **Preserve configuration** - do not modify `.env` files
- **Check container names** - use `docker ps` before running container commands
- **Use modern Docker Compose** - always use `docker compose` not `docker-compose`

This plan provides a comprehensive, step-by-step approach to simplifying the queue/circuit breaker system while maintaining system reliability and following established patterns. Each step includes clear success criteria and validation strategies to ensure the implementation meets the specified requirements. 