# Perplexity Timing Logging Implementation Summary

## Overview

Successfully implemented comprehensive timing and logging functionality for the Perplexity service to debug rate limiting issues. The implementation adds detailed logging for each request attempt with timing information, rate limiter decisions, and response details.

## Problem Statement

With very conservative rate limiting (1 request every 5 seconds), the Perplexity rate limit was still being hit. The goal was to add detailed logging to understand why this was happening.

## Implementation Details

### 1. Enhanced ApiIntegrationRateLimiter

**File**: `app/core/api_integration_rate_limiter.py`

Added timing tracking capabilities:
- `get_last_request_time()`: Returns timestamp of last request
- `get_time_since_last_request()`: Returns seconds since last request
- Redis-based persistence of timing data
- Graceful degradation when Redis is unavailable

**Key Features**:
- Timing data stored in Redis with TTL
- Thread-safe operations
- Consistent across multiple service instances

### 2. Enhanced PerplexityService

**File**: `app/background_services/perplexity_service.py`

Added comprehensive logging methods:
- `_log_request_attempt()`: Logs each request attempt with timing details
- `_log_request_response()`: Logs response details and timing
- `_check_rate_limit()`: Enhanced rate limit checking with logging

**Key Features**:
- Correlation IDs for request tracing
- Detailed timing measurements
- Rate limiter decision logging
- Response time tracking
- Structured logging with extra fields

### 3. Log Format

Each request generates two main log entries:

#### Request Attempt Log
```
perplexity timing test log - Request Attempt: 
correlation_id=<uuid>, 
timestamp=<iso_timestamp>Z, 
time_since_last_request=<seconds>, 
rate_limiter_decision=<allowed|denied|no_limiter|error_fallback>, 
rate_limiter_remaining=<count>, 
lead_id=<id>, 
attempt_number=<1-3>
```

#### Request Response Log
```
perplexity timing test log - Request Response: 
correlation_id=<uuid>, 
response_status=<success|error|rate_limited>, 
response_time_ms=<milliseconds>, 
api_response_code=<http_code>, 
error_details=<details>
```

## Usage

### Filtering Logs
```bash
# View all perplexity timing logs
grep "perplexity timing test log" /path/to/logs

# View only request attempts
grep "perplexity timing test log - Request Attempt" /path/to/logs

# View only responses
grep "perplexity timing test log - Request Response" /path/to/logs

# Follow a specific request by correlation ID
grep "correlation_id=abc-123-def" /path/to/logs
```

### Log Analysis
The logs provide insights into:
- **Timing patterns**: How often requests are actually made
- **Rate limiter effectiveness**: Whether requests are being properly throttled
- **Response times**: API performance metrics
- **Error patterns**: Types and frequency of failures
- **Request correlation**: Tracing individual requests through retries

## Testing

### Unit Tests
- **File**: `app/background_services/smoke_tests/test_perplexity_service.py`
- 24 comprehensive tests covering all scenarios
- Tests for timing functionality, correlation IDs, and logging

### Integration Tests
- **File**: `tests/integration/rate_limiting/test_redis_integration.py`
- Tests with real Redis instance
- Timing persistence across service instances
- Graceful degradation scenarios

### Demo Script
- **File**: `scripts/test_perplexity_timing_logs.py`
- Demonstrates all logging scenarios
- Shows expected log output formats

## Configuration

The implementation uses existing configuration:
- `PERPLEXITY_RATE_LIMIT_REQUESTS`: Number of requests per period
- `PERPLEXITY_RATE_LIMIT_PERIOD`: Period in seconds
- Redis connection for timing persistence

## Backward Compatibility

- Fully backward compatible
- Rate limiting remains optional
- No breaking changes to existing APIs
- Graceful degradation when Redis unavailable

## Benefits

1. **Debugging Capability**: Easy identification of rate limiting issues
2. **Request Tracing**: Correlation IDs for following requests through logs
3. **Performance Monitoring**: Response time tracking
4. **Pattern Analysis**: Understanding actual vs. expected request timing
5. **Error Analysis**: Detailed error logging with context

## Example Log Output

```
2024-01-15T10:30:45.123Z INFO perplexity timing test log - Request Attempt: correlation_id=abc-123-def, timestamp=2024-01-15T10:30:45.123Z, time_since_last_request=5.2, rate_limiter_decision=allowed, rate_limiter_remaining=0, lead_id=lead-456, attempt_number=1

2024-01-15T10:30:45.456Z INFO perplexity timing test log - Request Response: correlation_id=abc-123-def, response_status=success, response_time_ms=333.45, api_response_code=200, error_details=None
```

## Next Steps

1. **Monitor Production Logs**: Use the new logging to identify rate limiting patterns
2. **Analyze Timing Data**: Look for unexpected request clustering
3. **Adjust Rate Limits**: Based on actual timing analysis
4. **Extend to Other Services**: Apply similar logging to other API services

## Files Modified

1. `app/core/api_integration_rate_limiter.py` - Added timing methods
2. `app/background_services/perplexity_service.py` - Added comprehensive logging
3. `app/background_services/smoke_tests/test_perplexity_service.py` - Updated tests
4. `tests/integration/rate_limiting/test_redis_integration.py` - Added timing tests
5. `app/core/alert_service.py` - Fixed import issue
6. `scripts/test_perplexity_timing_logs.py` - Demo script

## Test Results

- ✅ All 25 perplexity-related tests passing
- ✅ Timing functionality working with Redis
- ✅ Graceful degradation tested
- ✅ Correlation ID consistency verified
- ✅ Response timing accuracy validated

The implementation is ready for production use and will provide the detailed timing information needed to debug the rate limiting issues with Perplexity API. 