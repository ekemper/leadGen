# Perplexity Timing Test Log Implementation Plan

## Overview
Add comprehensive logging to the Perplexity service to track each request attempt and debug why conservative rate limiting (1 request every 5 seconds) is still hitting Perplexity's rate limits.

## Goals
- Log each attempt to make a call to Perplexity with detailed timing information
- Track time intervals between requests
- Monitor circuit breaker/rate limiter decisions
- Capture response details for analysis
- Enable easy grep-based log filtering for debugging

## Current Architecture Assessment

### Existing Rate Limiting Configuration
- **Rate Limit**: 1 request per 5 seconds (PERPLEXITY_RATE_LIMIT_REQUESTS=1, PERPLEXITY_RATE_LIMIT_PERIOD=5)
- **Implementation**: `ApiIntegrationRateLimiter` using Redis for distributed rate limiting
- **Integration**: Used in `campaign_tasks.py` via `PerplexityService`

### Current Logging Pattern
- Basic INFO level logging for success/failure
- Rate limit exceeded warnings
- Component-based logging with extra context

## Implementation Plan

### Step 1: Enhance ApiIntegrationRateLimiter with Timing Tracking
**Goal**: Add timing information to the rate limiter to track request intervals
**Actions**:
- Add `get_last_request_time()` method to return timestamp of last request
- Add `get_time_since_last_request()` method to calculate interval
- Store request timestamps in Redis with appropriate expiration
- Maintain backward compatibility

**Testing Strategy**: 
- Unit tests for new methods
- Integration tests with Redis
- Verify timing accuracy within milliseconds

### Step 2: Enhance PerplexityService Logging
**Goal**: Add comprehensive logging for each request attempt
**Actions**:
- Create structured logging method `_log_request_attempt()` 
- Log before each request attempt with:
  - Title: "perplexity timing test log"
  - Current timestamp
  - Time since last request
  - Rate limiter decision (allowed/denied)
- Log after each request with response details
- Include request correlation ID for tracing

**Testing Strategy**:
- Verify log format and content
- Test with rate limiter enabled/disabled
- Confirm grep-friendly log format

### Step 3: Add Request Tracking State
**Goal**: Track request state across attempts and retries
**Actions**:
- Add instance-level tracking of last request time
- Implement request correlation ID generation
- Track retry attempts with timing
- Store timing metrics for analysis

**Testing Strategy**:
- Test retry scenarios with timing
- Verify state consistency across requests
- Test concurrent access patterns

### Step 4: Comprehensive Integration Testing
**Goal**: Ensure logging works correctly in real scenarios
**Actions**:
- Test with actual Redis instance
- Verify log output in worker tasks
- Test circuit breaker integration
- Validate timing accuracy under load

**Testing Strategy**:
- Run `make docker-test` to verify all existing tests pass
- Add integration test for timing logging
- Test in Docker container environment

## Implementation Details

### New Log Format Specification
```
[TIMESTAMP] [LEVEL] perplexity timing test log - Request Attempt
  - correlation_id: <uuid>
  - timestamp: <iso_timestamp>
  - time_since_last_request: <seconds_float>
  - rate_limiter_decision: <allowed|denied>
  - rate_limiter_remaining: <count>
  - lead_id: <lead_id>
  - attempt_number: <1-3>

[TIMESTAMP] [LEVEL] perplexity timing test log - Request Response  
  - correlation_id: <uuid>
  - response_status: <success|error|rate_limited>
  - response_time_ms: <milliseconds>
  - api_response_code: <http_code>
  - error_details: <if_applicable>
```

### Redis Key Structure for Timing
```
ratelimit:Perplexity:last_request - timestamp of last successful request
ratelimit:Perplexity:request_log:<correlation_id> - detailed request log
```

### Backward Compatibility Requirements
- Existing rate limiting behavior unchanged
- All existing tests must pass
- No breaking changes to service interfaces
- Graceful degradation if Redis unavailable

## General Implementation Rules

### Critical Assessment and Clarification
- **Question**: Is 5-second rate limiting truly conservative for Perplexity's API?
- **Consideration**: Are there multiple instances/workers making concurrent requests?
- **Analysis**: Could Redis distributed locking have race conditions?

### Code Quality Standards
- Follow existing logging patterns in the codebase
- Use structured logging with consistent extra fields
- Add comprehensive docstrings for new methods
- Maintain consistent error handling patterns

### Testing Requirements
- All new code must have unit tests
- Integration tests for Redis timing functionality
- Functional tests hitting actual API endpoints in test containers
- Run tests in Docker containers: `docker exec api pytest ...`
- Full test suite: `make docker-test`

### Database and Migration Considerations
- No database changes required for this implementation
- Redis-only state management for timing data
- Consider Redis memory usage for timing logs

### Performance Considerations
- Minimize Redis calls for timing operations
- Use pipeline operations where possible
- Set appropriate TTL for timing logs
- Monitor Redis memory usage

### Security and Data Handling
- No sensitive data in timing logs
- Sanitize any response data before logging
- Use correlation IDs instead of sensitive identifiers

### Deployment Considerations
- Changes are backward compatible
- No environment variable changes required
- Redis configuration should handle additional keys
- Log volume may increase - monitor disk usage

## Step-by-Step Implementation

### Phase 1: Rate Limiter Enhancement
1. Modify `ApiIntegrationRateLimiter` to track timing
2. Add timing methods with Redis backend
3. Write comprehensive unit tests
4. Test Redis integration scenarios

### Phase 2: Service Logging Enhancement  
1. Add structured logging to `PerplexityService`
2. Implement request correlation tracking
3. Add timing calculations and logging
4. Write service-level tests

### Phase 3: Integration and Validation
1. Test with worker tasks in Docker containers
2. Verify log output format and grep-ability
3. Run full test suite to ensure no regressions
4. Validate timing accuracy under various load conditions

### Phase 4: Documentation and Monitoring
1. Document new logging format for operations team
2. Create log analysis scripts/queries
3. Set up monitoring for timing patterns
4. Document troubleshooting procedures

## Success Criteria
- All existing tests pass (`make docker-test`)
- New timing logs are easily grep-able with "perplexity timing test log"
- Timing accuracy within 100ms tolerance
- Rate limiter decisions correctly logged
- Response details captured for analysis
- No performance degradation in service response times
- Backward compatibility maintained

## Risk Mitigation
- Redis failure handling with graceful degradation
- Log volume management with appropriate retention
- Performance monitoring during implementation
- Rollback plan if issues discovered

## Post-Implementation Analysis
After implementation, the logs will enable analysis of:
- Actual time intervals between Perplexity requests
- Rate limiter effectiveness and accuracy
- Potential race conditions in distributed rate limiting
- API response patterns and error rates
- Worker task timing and scheduling patterns

This analysis should reveal why conservative rate limiting is still hitting Perplexity's limits and guide further optimization. 