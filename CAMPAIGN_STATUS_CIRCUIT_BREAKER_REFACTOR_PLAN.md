# Campaign Status and Circuit Breaker Refactor Implementation Plan

## Executive Summary

**Current Issue**: The existing system has complex automatic campaign resume logic that needs to be removed. Campaigns should only be paused automatically when circuit breakers open or queues are paused, but resumed ONLY through manual user action via the queue management API.

**Goal**: Create a simplified, predictable system where:
- Campaigns pause automatically when ANY job is paused OR when queue is paused
- Circuit breaker opening pauses ALL campaigns and the queue immediately
- Campaigns resume ONLY through manual queue resume action
- Manual queue resume only works if ALL circuit breakers are closed

## Technical Assessment of Current Architecture

### Current Models and Relationships
- **Campaign Model**: Has proper status enum with PAUSED state and transition validation
- **Job Model**: Has JobStatus.PAUSED with campaign relationship 
- **Circuit Breaker**: Uses Redis for state management with proper event handling
- **API Pattern**: Standardized JSON responses with status/data structure

### Current Services Analysis
- **CampaignStatusMonitor**: Contains complex automatic resume logic (NEEDS REMOVAL)
- **CircuitBreakerService**: Proper state management but triggers complex campaign logic
- **CampaignEventHandler**: Handles circuit breaker events with sophisticated logic (NEEDS SIMPLIFICATION)
- **QueueManagementAPI**: Already has proper endpoints for manual control

### Current Testing Patterns
- **API-level functional tests**: Hit endpoints and verify database state
- **Docker container execution**: Tests run in `leadgen-api-1` container
- **Database verification**: Tests check actual DB state after API calls
- **Authentication**: Uses `authenticated_client` fixture

## Business Rules (Simplified)

### Campaign Pause Logic (Automatic)
1. **ANY job paused** → Campaign MUST be paused immediately
2. **Queue paused** → ALL campaigns MUST be paused immediately  
3. **Circuit breaker opens** → Queue pauses → ALL campaigns pause → all jobs pause

### Campaign Resume Logic (Manual Only)
1. **Queue resume button** → Only way to resume campaigns
2. **Prerequisite check** → ALL circuit breakers MUST be closed
3. **Job resume** → Paused jobs resume when campaign resumes
4. **NO automatic resume** → Remove all existing automatic resume logic

### Circuit Breaker Integration
1. **ANY service error** → Circuit breaker opens immediately
2. **Circuit breaker open** → Queue pauses immediately
3. **Manual reset** → User can reset circuit breaker, but campaigns still need manual resume

## Implementation Plan

### Phase 1: Comprehensive Test Coverage (Steps 1-5)

#### Step 1: Create New Campaign Status Logic Tests
**Goal**: Create comprehensive tests for the new simplified campaign status logic
**Actions**:
- Create `test_campaign_status_refactor.py` with complete coverage
- Test automatic pause scenarios (job pause, queue pause, circuit breaker)
- Test manual resume scenarios (queue resume button)
- Test prerequisite validation (circuit breaker checks)
- Test edge cases and error conditions

**Success Criteria**: 
- All new test scenarios pass
- Complete coverage of new business rules
- Database state verification in all tests

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_campaign_status_refactor.py -v
```

#### Step 2: Update Existing Queue Management Tests  
**Goal**: Update existing tests to match new simplified logic
**Actions**:
- Update `test_queue_management_api.py` to remove automatic resume expectations
- Modify tests to expect only manual resume through queue management
- Add tests for circuit breaker prerequisite checking
- Update test assertions to match new behavior

**Success Criteria**: 
- All existing queue management tests pass with new logic
- No broken test expectations from old automatic resume behavior

#### Step 3: Create Circuit Breaker Integration Tests
**Goal**: Test circuit breaker integration with new simplified campaign logic
**Actions**:
- Update `test_circuit_breaker_integration.py` for new behavior
- Test circuit breaker open → queue pause → campaign pause chain
- Test manual circuit breaker reset (without automatic campaign resume)
- Test queue resume with circuit breaker prerequisite validation

**Success Criteria**: 
- Circuit breaker events properly pause campaigns and queue
- Manual operations work correctly with prerequisite validation

#### Step 4: Create Job Status Integration Tests
**Goal**: Test job status changes trigger correct campaign status updates  
**Actions**:
- Create comprehensive tests for job pause → campaign pause
- Test job resume scenarios (through campaign resume)
- Test mixed job status scenarios within campaigns
- Test job status updates in paused vs running campaigns

**Success Criteria**: 
- Job status changes properly trigger campaign evaluations
- Campaign status correctly reflects job states

#### Step 5: Validate Complete Test Suite
**Goal**: Ensure all tests work together and cover complete system behavior
**Actions**:
- Run complete test suite to identify conflicts
- Fix any test interactions or dependencies
- Validate test execution order independence
- Ensure database cleanup between tests

**Success Criteria**: 
- Full test suite passes: `make docker-test`
- Tests can run independently and in any order
- No test pollution or state dependencies

### Phase 2: Core Service Refactoring (Steps 6-10)

#### Step 6: Simplify CampaignStatusMonitor Service
**Goal**: Remove all automatic resume logic, keep only pause logic
**Actions**:
- Remove `evaluate_campaigns_for_service_recovery()` method
- Remove `evaluate_campaign_resumption()` method  
- Remove `_can_resume_campaign_safely()` method
- Keep only `evaluate_campaign_status_for_service()` for pause logic
- Simplify to focus on "ANY job paused → campaign paused" rule

**Success Criteria**: 
- Service only handles pause logic
- No automatic resume capabilities remain
- Simplified, predictable behavior

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_campaign_status_refactor.py::test_campaign_status_monitor_pause_only -v
```

#### Step 7: Simplify CampaignEventHandler
**Goal**: Remove automatic resume logic, simplify to pause-only event handling
**Actions**:
- Remove `handle_circuit_breaker_closed()` campaign resume logic
- Keep `handle_circuit_breaker_opened()` for pause logic
- Remove `_can_resume_campaign_safely()` method
- Remove `_resume_campaign_if_safe()` method
- Simplify `handle_circuit_breaker_half_open()` to log-only

**Success Criteria**: 
- Event handler only pauses campaigns when circuit breaker opens
- No automatic resume on circuit breaker close
- Clean, simple event handling

#### Step 8: Update CircuitBreakerService Integration  
**Goal**: Ensure circuit breaker events properly pause queue and campaigns
**Actions**:
- Verify `_pause_service_queues()` pauses queue when circuit opens
- Remove any automatic resume triggers in circuit breaker
- Ensure circuit breaker state transitions don't trigger campaign resume
- Keep manual reset capability for circuit breakers

**Success Criteria**: 
- Circuit breaker opening pauses queue immediately
- Queue pausing triggers campaign pausing
- Circuit breaker closing does NOT resume campaigns automatically

#### Step 9: Implement Manual Resume Logic in Queue Management
**Goal**: Create manual resume logic that checks circuit breaker prerequisites
**Actions**:
- Update queue management API resume endpoint
- Add circuit breaker prerequisite validation
- Implement "resume queue → resume campaigns → resume jobs" chain
- Add proper error handling for prerequisite failures

**Success Criteria**: 
- Manual queue resume only works if all circuit breakers closed
- Queue resume properly resumes all paused campaigns
- Campaign resume properly resumes all paused jobs

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_queue_management_api.py::test_manual_resume_with_prerequisites -v
```

#### Step 10: Implement Job Status → Campaign Status Logic
**Goal**: Ensure ANY paused job immediately pauses its campaign
**Actions**:
- Create job status change handler
- Implement immediate campaign pause when any job pauses
- Add campaign status evaluation on job status changes
- Ensure proper database transaction handling

**Success Criteria**: 
- Single paused job pauses entire campaign
- Campaign status updates immediately on job status change
- Proper transactional consistency

### Phase 3: API and Integration Updates (Steps 11-13)

#### Step 11: Update Queue Management API Endpoints
**Goal**: Ensure API endpoints implement new manual-only resume logic
**Actions**:
- Update queue resume endpoint with prerequisite validation
- Remove any automatic resume triggers from other endpoints
- Add circuit breaker status checks to resume operations
- Enhance error messages for failed prerequisite checks

**Success Criteria**: 
- Queue resume endpoint validates all circuit breakers are closed
- Clear error messages when prerequisites not met
- No automatic resume triggers in any endpoint

#### Step 12: Update Campaign Service Integration
**Goal**: Remove automatic resume logic from campaign service
**Actions**:
- Remove automatic resume methods from CampaignService
- Keep manual pause capabilities for direct campaign control
- Update campaign start validation to check circuit breaker states
- Ensure campaign service respects new pause/resume rules

**Success Criteria**: 
- Campaign service has no automatic resume logic
- Campaign operations respect circuit breaker and queue states
- Manual campaign operations work correctly

#### Step 13: Update Background Task Integration
**Goal**: Ensure background tasks respect new campaign status logic
**Actions**:
- Add campaign status checks to all job processing tasks
- Ensure paused campaigns don't process jobs
- Add proper task queuing when campaigns are paused
- Implement task resume when campaigns are manually resumed

**Success Criteria**: 
- Background tasks respect campaign pause status
- No job processing for paused campaigns
- Tasks resume properly when campaigns manually resumed

### Phase 4: Frontend Integration (Steps 14-15)

#### Step 14: Update Frontend Queue Management Interface
**Goal**: Update frontend to support new manual-only resume workflow
**Actions**:
- Update queue management UI to clearly show manual resume requirement
- Add circuit breaker status display with prerequisite warnings
- Update messaging to explain manual resume requirements
- Add loading states for manual resume operations

**Success Criteria**: 
- Frontend clearly communicates manual resume requirements
- Circuit breaker status visible to users
- Clear feedback on prerequisite failures

#### Step 15: Validate End-to-End Workflow
**Goal**: Test complete workflow from circuit breaker event to manual resume
**Actions**:
- Create end-to-end test scenario
- Test: Service failure → Circuit breaker open → Queue pause → Campaign pause
- Test: Manual circuit breaker reset → Manual queue resume → Campaign resume
- Validate UI feedback and database state throughout workflow

**Success Criteria**: 
- Complete workflow works as designed
- UI provides clear feedback at each step
- Database state consistent throughout process

### Phase 5: System Flow Documentation (Steps 16-18)

#### Step 16: Document Service Error → System Pause Flow
**Goal**: Create comprehensive documentation of the service failure cascade
**Actions**:
- Document the complete flow: Service Error → Circuit Breaker Open → Queue Pause → Campaign Pause → Job Pause
- Include timing considerations and error propagation
- Document database state changes at each step
- Include logging and monitoring points throughout the flow
- Create sequence diagrams for technical documentation
- Save documents in md files

**Detailed Flow Outline**:
```
SERVICE ERROR FLOW:
1. Third-party service (Apollo/Perplexity/OpenAI/Instantly/MillionVerifier) throws error
2. Error captured by service wrapper → Circuit breaker records failure
3. Circuit breaker failure count reaches threshold → Circuit breaker opens (state: CLOSED → OPEN)
4. Circuit breaker opening triggers _pause_service_queues() → Queue status set to PAUSED
5. Queue pause triggers campaign_event_handler.handle_circuit_breaker_opened()
6. Campaign event handler evaluates ALL running campaigns → Pauses ALL campaigns (status: RUNNING → PAUSED)
7. Campaign pause propagates to jobs → ALL jobs paused (status: PENDING/PROCESSING → PAUSED)
8. System state: Circuit Breaker OPEN + Queue PAUSED + All Campaigns PAUSED + All Jobs PAUSED
9. Background tasks stop processing due to paused state
10. Frontend shows circuit breaker status and manual resume requirement
```

**Success Criteria**: 
- Complete flow documented with timing and state transitions
- Error propagation paths clearly defined
- Database state changes documented
- Technical sequence diagrams created

#### Step 17: Document Manual Circuit Breaker Reset Flow
**Goal**: Document the circuit breaker reset process and its limited effects
**Actions**:
- Document manual circuit breaker reset through API
- Clarify that circuit breaker reset does NOT automatically resume campaigns
- Document the separation between circuit breaker state and campaign state
- Include user workflow for circuit breaker management
- process is documented in md file

**Detailed Flow Outline**:
```
MANUAL CIRCUIT BREAKER RESET FLOW:
1. User clicks "Reset Circuit Breaker" button in UI for specific service
2. Frontend calls POST /api/v1/queue-management/circuit-breakers/{service}/reset
3. CircuitBreakerService.manually_reset_circuit() executes
4. Circuit breaker state changes: OPEN → CLOSED
5. Queue remains PAUSED (circuit breaker reset does NOT resume queue)
6. Campaigns remain PAUSED (circuit breaker reset does NOT resume campaigns)
7. Jobs remain PAUSED (no automatic resume cascade)
8. System state: Circuit Breaker CLOSED + Queue PAUSED + All Campaigns PAUSED + All Jobs PAUSED
9. Frontend updates circuit breaker status display
10. User must SEPARATELY use "Resume Queue" button to resume operations
```

**Success Criteria**: 
- Manual reset process clearly documented
- Separation of circuit breaker and campaign states explained
- User workflow steps defined
- No automatic resume behavior documented

#### Step 18: Document Manual Queue Resume Flow
**Goal**: Document the complete manual resume process through queue management
**Actions**:
- Document the manual queue resume workflow
- Include circuit breaker prerequisite validation
- Document the cascade: Queue Resume → Campaign Resume → Job Resume
- Include error handling for failed prerequisites

**Detailed Flow Outline**:
```
MANUAL QUEUE RESUME FLOW:
1. User clicks "Resume Queue" button in UI
2. Frontend calls POST /api/v1/queue-management/resume-service
3. Queue Management API validates ALL circuit breakers are CLOSED
4. If any circuit breaker is OPEN → Return error "Cannot resume: Circuit breaker {service} is open"
5. If all circuit breakers CLOSED → Proceed with resume
6. Queue status changes: PAUSED → ACTIVE
7. Queue resume triggers campaign resume logic for ALL paused campaigns
8. Campaign status changes: PAUSED → RUNNING (for all campaigns)
9. Campaign resume triggers job resume logic
10. Job status changes: PAUSED → PENDING/PROCESSING (jobs resume processing)
11. Background tasks resume processing jobs
12. System state: All Circuit Breakers CLOSED + Queue ACTIVE + All Campaigns RUNNING + All Jobs ACTIVE
13. Frontend updates all status displays
```

**Success Criteria**: 
- Complete manual resume workflow documented
- Prerequisite validation process defined
- Cascade effects clearly explained
- Error handling scenarios documented

### Phase 6: Test Integration and Refactoring (Steps 19-20)

#### Step 19: Refactor test_concurrent_campaigns_flow for Queue Awareness
**Goal**: Update the concurrent campaigns test to be fully aware of queue status and circuit breaker integration
**Actions**:
- Integrate queue status monitoring throughout test execution
- Add queue status endpoint calls to track queue state changes
- Implement intelligent test termination when queue pauses due to circuit breaker
- Add comprehensive final reporting for paused state scenarios
- Update test to validate the new pause/resume logic

**Detailed Test Refactor Requirements**:
```python
# New test structure requirements:
1. Pre-flight Queue Status Check:
   - Call GET /api/v1/queue-management/status before starting
   - Verify queue is ACTIVE and all circuit breakers CLOSED
   - Abort test if queue is PAUSED or circuit breakers OPEN

2. Continuous Queue Monitoring:
   - Call queue status endpoint every 10 seconds during execution
   - Monitor queue_paused field and circuit breaker states
   - Detect queue pause events immediately

3. Circuit Breaker Triggered Pause Handling:
   - When queue becomes PAUSED due to circuit breaker:
     * Stop all campaign creation/monitoring
     * Call campaign status API to get final campaign states  ( may need to implement a waiting period for campaign and job states to update after circuit breaker triggers )
     * Call job status API to get final job states
     * Generate comprehensive final report
     * Terminate test gracefully (not as failure)

4. Enhanced Reporting:
   - Report queue status at each phase
   - Include circuit breaker status in all status reports
   - Show campaign pause reasons when applicable
   - Document which campaigns/jobs were affected by pause

5. Test Scenario:
This is inteded to be a full integration test. several campaigns with many jobs and leads should result. the test needs to report real world metrics and conditions that evolve during the test:
   - Happy path: if there are No service failures, test completes normally
   - Service failure information surfaceing : Circuit breaker triggers, queue pauses, test reports and exits
   - Mixed scenarios reporting : Some campaigns complete before circuit breaker triggers
```

**Success Criteria**: 
- Test correctly monitors queue status throughout execution
- Test handles circuit breaker-triggered pauses gracefully
- Comprehensive reporting for both success and pause scenarios
- Test validates new pause/resume logic behavior

#### Step 20: Create Queue Status Integration Test
**Goal**: Create dedicated test for queue status monitoring and manual resume workflows
**Actions**:
- Create `test_queue_status_integration.py` for comprehensive queue monitoring
- Test queue status endpoint accuracy during various system states
- Test manual queue resume workflow with prerequisite validation
- Test circuit breaker reset and queue resume separation
- Validate queue status changes propagate correctly to campaigns and jobs

**Test Coverage Requirements**:
```python
# Required test scenarios:
1. test_queue_status_accuracy_during_normal_operations
2. test_queue_status_during_circuit_breaker_trigger
3. test_manual_queue_resume_with_all_circuit_breakers_closed
4. test_manual_queue_resume_blocked_by_open_circuit_breaker
5. test_circuit_breaker_reset_does_not_resume_queue
6. test_queue_resume_cascade_to_campaigns_and_jobs
7. test_queue_status_endpoint_real_time_updates
8. test_multiple_circuit_breaker_failures_and_manual_recovery
```

**Success Criteria**: 
- Complete queue status monitoring test coverage
- Manual resume workflow fully validated
- Circuit breaker and queue state separation tested
- Real-time status update accuracy verified

**Validation Strategy**:
```bash
docker exec leadgen-api-1 pytest tests/test_queue_status_integration.py -v
docker exec leadgen-api-1 python app/background_services/smoke_tests/test_concurrent_campaigns_flow.py
```

## Database Migration Requirements

### New Database Fields (if needed)
- No new tables required
- Existing campaign and job status fields sufficient
- Circuit breaker state stored in Redis (existing)

### Migration Commands
```bash
# If any schema changes needed:
docker exec leadgen-api-1 alembic revision --autogenerate -m "Campaign status refactor schema updates"
docker exec leadgen-api-1 alembic upgrade head
```

## Testing Strategy

### Test Execution Pattern
```bash
# Individual test development
docker exec leadgen-api-1 pytest tests/test_campaign_status_refactor.py::test_specific_scenario -v

# Service-level testing  
docker exec leadgen-api-1 pytest tests/test_campaign_status_refactor.py -v

# Integration testing
docker exec leadgen-api-1 pytest tests/test_queue_management_api.py -v

# Queue status integration testing
docker exec leadgen-api-1 pytest tests/test_queue_status_integration.py -v

# Concurrent campaigns flow testing
docker exec leadgen-api-1 python app/background_services/smoke_tests/test_concurrent_campaigns_flow.py

# Full suite validation
make docker-test
```

### Test Categories
1. **Unit Tests**: Individual service methods
2. **Integration Tests**: API endpoints with database verification  
3. **End-to-End Tests**: Complete workflow scenarios
4. **Edge Case Tests**: Error conditions and boundary scenarios
5. **Queue Monitoring Tests**: Real-time status tracking and manual resume workflows
6. **Concurrent Flow Tests**: Multi-campaign scenarios with circuit breaker awareness

## Success Criteria

### Functional Requirements Met
- ✅ Campaigns pause when ANY job paused
- ✅ Campaigns pause when queue paused
- ✅ Circuit breaker opening pauses queue and campaigns
- ✅ Manual resume only through queue management API
- ✅ Resume requires all circuit breakers closed
- ✅ No automatic resume logic remains
- ✅ Complete system flow documentation created
- ✅ Queue status monitoring integrated into tests
- ✅ Concurrent campaigns test refactored for queue awareness

### Technical Requirements Met
- ✅ All tests pass (100% coverage for new logic)
- ✅ Existing patterns and conventions maintained
- ✅ API responses follow standard format
- ✅ Database transactions handled properly
- ✅ Error handling comprehensive
- ✅ Logging and monitoring maintained
- ✅ Real-time queue status monitoring functional
- ✅ Manual resume workflows fully validated

### User Experience Requirements Met
- ✅ Clear feedback on manual resume requirements
- ✅ Circuit breaker status visible in UI
- ✅ Predictable campaign behavior
- ✅ No surprising automatic resume actions
- ✅ Queue status clearly communicated to users
- ✅ Manual resume process intuitive and reliable

## General Implementation Rules

### Technical Assessment Rule
- **ALWAYS question and validate** user requirements against technical feasibility
- **ASK for clarification** when requirements are unclear or potentially problematic
- **PROVIDE rationale** for all technical decisions and implementation choices

### Code Quality Rules
- **NEVER MAKE ASSUMPTIONS** - always provide clear rationale for implementation decisions
- **MAINTAIN PATTERNS** - follow existing code patterns and conventions consistently
- **UPDATE TESTS IMMEDIATELY** - never make code changes without corresponding test updates
- **COMPREHENSIVE ERROR HANDLING** - handle all error conditions with proper logging

### Testing Rules
- **API-LEVEL TESTS** - all tests must hit API endpoints and verify database state
- **DOCKER EXECUTION** - run all tests and commands in appropriate docker containers
- **INDIVIDUAL AND SUITE** - tests must pass individually and as part of complete suite
- **DATABASE VERIFICATION** - verify actual database state, not just API responses

### Migration and Deployment Rules
- **USE ALEMBIC COMMANDS** - `alembic revision --autogenerate` and `alembic upgrade head` for migrations
- **CONTAINER EXECUTION** - run database commands in API docker container
- **NO ENV MODIFICATIONS** - do not create or modify environment files
- **CONFIGURATION REQUESTS** - ask user for any needed configuration changes

### Documentation Rules
- **COPIOUS COMMENTS** - add detailed comments explaining business logic decisions
- **DOCSTRINGS** - comprehensive docstrings for all new methods and classes
- **MARKDOWN DOCS** - create documentation files for significant pattern changes
- **SOURCE OF TRUTH** - update documentation to reflect new patterns and rules

## Risk Assessment and Mitigation

### Technical Risks
1. **Race Conditions**: Job status changes and campaign status updates
   - **Mitigation**: Proper database transaction handling and locking
2. **State Inconsistency**: Circuit breaker and campaign status misalignment  
   - **Mitigation**: Comprehensive integration tests and state validation
3. **Performance Impact**: Additional status checks on job operations
   - **Mitigation**: Efficient database queries and caching where appropriate

### User Experience Risks
1. **Confusion**: Manual resume requirement not clear to users
   - **Mitigation**: Clear UI messaging and comprehensive user feedback
2. **Frustration**: Cannot resume campaigns when expected
   - **Mitigation**: Clear prerequisite messaging and circuit breaker status display

### Business Logic Risks
1. **Over-Pausing**: Too many campaigns paused for minor issues
   - **Mitigation**: Proper testing of pause triggers and clear resume process
2. **Under-Pausing**: Missing edge cases where campaigns should pause
   - **Mitigation**: Comprehensive test coverage of all pause scenarios

This implementation plan provides a comprehensive, step-by-step approach to refactoring the campaign status and circuit breaker integration according to the specified requirements. Each step has clear goals, actions, success criteria, and validation strategies. 