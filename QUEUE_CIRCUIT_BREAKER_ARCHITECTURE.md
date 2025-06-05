# Queue and Circuit Breaker Architecture Documentation

## Executive Summary

This document describes the **simplified** queue and circuit breaker architecture implemented to replace the previous complex service-specific system. The new architecture follows the principle of "Single Source of Truth" with global circuit breaker state and manual-only recovery.

## Core Principles

### 1. Global Circuit Breaker State
- **Only two states**: `OPEN` (system down) and `CLOSED` (system working)
- **Single global state** - not service-specific
- **Any service error** immediately opens the global circuit breaker
- **All services affected equally** when circuit breaker opens

### 2. Manual-Only Recovery
- **No automatic closing** - circuit breaker never closes automatically
- **Frontend-controlled recovery** - only manual API calls can close circuit breaker
- **Deliberate intervention required** - ensures human oversight of recovery

### 3. Job-Level State Management
- **Jobs pause**, campaigns remain RUNNING
- **Global pause/resume** - all active jobs affected simultaneously
- **Circuit breaker drives job state** - jobs pause when circuit opens, resume when circuit closes

## Architecture Components

### Circuit Breaker Service (`app/core/circuit_breaker.py`)

```python
class CircuitBreakerService:
    """Simplified global circuit breaker with manual-only closing."""
    
    def record_failure(self, error: str, error_type: str = "unknown") -> bool:
        """Any failure immediately opens circuit breaker."""
        
    def record_success(self):
        """Success does NOT automatically close circuit."""
        
    def manually_close_circuit(self):
        """ONLY way to close circuit breaker."""
        
    def should_allow_request(self) -> bool:
        """Check global circuit state only."""
```

#### Key Features:
- **Immediate failure response**: Any error from any service opens circuit
- **Global state storage**: Redis key `circuit_breaker:global` 
- **Automatic job pausing**: Circuit opening triggers job pause cascade
- **Manual intervention required**: Only API calls can close circuit

### Queue Manager (`app/core/queue_manager.py`)

```python
class QueueManager:
    """Simplified queue management with global circuit breaker integration."""
    
    def should_process_job(self) -> bool:
        """Check global circuit breaker only."""
        
    def pause_all_jobs_on_breaker_open(self, reason: str) -> int:
        """Pause all PENDING/PROCESSING jobs."""
        
    def resume_all_jobs_on_breaker_close(self) -> int:
        """Resume all PAUSED jobs with new celery tasks."""
```

#### Key Features:
- **No service-specific logic** - all jobs treated equally
- **Atomic operations** - bulk job state changes with database transactions
- **Celery task recreation** - new tasks created for resumed jobs
- **Comprehensive error handling** - failed resumes marked as FAILED

### Job Resume Service (`app/services/job_resume_service.py`)

```python
class JobResumeService:
    """Reliable bulk job resume with retry logic."""
    
    def resume_all_paused_jobs(self, reason: str) -> Dict[str, Any]:
        """Resume all paused jobs with detailed status reporting."""
        
    def get_resume_status(self) -> Dict[str, Any]:
        """Get current resume-eligible job status."""
```

#### Key Features:
- **Batch processing** - handles large numbers of jobs efficiently
- **Retry logic** - multiple attempts for celery task creation
- **Detailed reporting** - comprehensive status and error tracking
- **Transaction safety** - atomic database operations

## Service Integration Pattern

All third-party service integrations follow the same pattern:

```python
# Before calling service
if not circuit_breaker.should_allow_request():
    return {"status": "circuit_breaker_open", "error": "Service unavailable"}

try:
    # Call service
    result = service.call_api()
    circuit_breaker.record_success()
    return result
except Exception as e:
    # Global circuit breaker - no service-specific logic
    circuit_breaker.record_failure(f"Service error: {str(e)}", "exception")
    raise
```

## Campaign State Simplification

### Removed States and Logic
- ❌ **Campaign PAUSED state** - campaigns never pause
- ❌ **Service-specific dependencies** - no unavailable_services tracking
- ❌ **Automatic campaign pausing** - campaigns remain RUNNING during circuit breaker events

### Current Campaign States
- ✅ **CREATED** - ready to start
- ✅ **RUNNING** - actively processing (continues even when circuit breaker opens)
- ✅ **COMPLETED** - all jobs finished successfully
- ✅ **FAILED** - campaign failed due to unrecoverable error

## API Endpoints

### Circuit Breaker Control
```
POST /api/v1/queue-management/circuit-breaker/close
```
- **Only endpoint** that can close circuit breaker
- **Requires authentication** and proper authorization
- **Triggers job resume** automatically when circuit closes

### Queue Status
```
GET /api/v1/queue-management/status
```
- **Global circuit breaker state**
- **Job counts by status**
- **Resume eligibility status**

### Job Status
```
GET /api/v1/jobs/{job_id}/status
```
- **Circuit breaker context** included in response
- **Pause reason** and **resume availability** for paused jobs
- **Real-time circuit breaker state**

## Data Flow

### Error Detection and Circuit Opening
```
Service Error → record_failure() → Circuit OPEN → pause_all_jobs() → Jobs become PAUSED
```

### Manual Recovery
```
Frontend Action → POST /circuit-breaker/close → Circuit CLOSED → resume_all_jobs() → Jobs become PENDING
```

### Job Processing Check
```
Job Processing → should_process_job() → Check Global Circuit → Allow/Block Processing
```

## Redis Data Structure

### Global Circuit Breaker
```redis
Key: "circuit_breaker:global"
Value: {
    "state": "closed|open",
    "opened_at": "2024-01-01T12:00:00Z",
    "closed_at": "2024-01-01T12:15:00Z", 
    "metadata": {
        "last_error": "Apollo service timeout",
        "error_type": "timeout",
        "failed_at": "2024-01-01T12:00:00Z"
    }
}
TTL: 86400 seconds (24 hours)
```

### Queue Status
```redis
Key: "queue_status:global"
Value: {
    "circuit_breaker_state": "closed|open",
    "total_paused_jobs": 42,
    "last_updated": "2024-01-01T12:00:00Z"
}
```

## Error Handling and Recovery

### Failure Scenarios and Responses
1. **Any Third-Party Service Error**:
   - Circuit breaker opens immediately
   - All active jobs pause
   - Alert sent to administrators
   - Manual intervention required

2. **Celery Task Creation Failure**:
   - Job marked as FAILED with detailed error
   - Other jobs continue processing
   - Retry logic for transient failures

3. **Database Transaction Failure**:
   - Rollback to consistent state
   - Error logged with context
   - Graceful degradation

### Recovery Process
1. **Identify Root Cause**: Investigate service error logs
2. **Fix Service Issues**: Resolve underlying service problems
3. **Manual Circuit Close**: Use frontend to close circuit breaker
4. **Verify Job Resume**: Monitor job processing resumption
5. **Validate System Health**: Confirm normal operations

## Monitoring and Alerting

### Key Metrics
- **Circuit breaker state changes**
- **Job pause/resume counts**
- **Service error rates**
- **Queue processing times**

### Alert Triggers
- Circuit breaker opens (CRITICAL)
- Job resume failures (WARNING)
- Service error spikes (WARNING)
- Extended circuit open duration (CRITICAL)

## Performance Characteristics

### Simplified Benefits
- **Faster failure detection** - immediate circuit opening
- **Reduced complexity** - single global state vs. multiple service states
- **Predictable behavior** - clear manual recovery path
- **Better reliability** - fewer race conditions and edge cases

### Scale Considerations
- **Batch job operations** - efficient handling of large job volumes
- **Redis performance** - minimal key usage with global state
- **Database efficiency** - atomic bulk operations
- **Memory usage** - simplified state tracking

## Testing Strategy

### Integration Tests
- **Circuit breaker state transitions**
- **Job pause/resume cycles**
- **Service error scenarios**
- **Manual recovery workflows**

### Load Testing
- **Large job volume handling**
- **Concurrent circuit breaker operations**
- **Database transaction performance**
- **Redis connection stability**

## Migration Notes

### Breaking Changes from Previous System
1. **No service-specific circuit breakers** - all services use global state
2. **No automatic circuit closing** - manual intervention required
3. **No campaign pausing** - only jobs pause
4. **No unavailable_services concept** - circuit breaker is single source of truth

### Backward Compatibility
- **API response formats** maintained where possible
- **Database schema** updated via migrations
- **Service integrations** updated to use global circuit breaker

This simplified architecture provides predictable, reliable queue management with clear manual recovery paths and minimal complexity. 