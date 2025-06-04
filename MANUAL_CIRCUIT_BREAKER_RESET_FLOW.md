# Manual Circuit Breaker Reset Flow Documentation

## Overview

This document details the manual circuit breaker reset process and its limited effects. Circuit breaker reset is designed to clear the failure state of a specific service but does NOT automatically resume campaigns or jobs. This separation ensures predictable system behavior and prevents unexpected automatic resumption.

## Flow Sequence

### 1. User Initiates Reset
**What happens:** User clicks "Reset Circuit Breaker" button in UI for specific service
**Location:** Frontend - `QueueMonitoringDashboard.tsx`
**Prerequisites:** Circuit breaker must be in OPEN state
**User Action:** Single button click with service confirmation

```typescript
// Frontend reset trigger
const resetCircuitBreaker = async (service: string) => {
    const data = await api.post(`/queue-management/circuit-breakers/${service}/reset`);
    // UI feedback provided
}
```

### 2. API Endpoint Processing
**What happens:** Frontend calls `POST /api/v1/queue-management/circuit-breakers/{service}/reset`
**Location:** `app/api/endpoints/queue_management.py` - `reset_circuit_breaker()`
**Timing:** Immediate HTTP request processing
**Validation:** Service name validation against ThirdPartyService enum

```python
@router.post("/circuit-breakers/{service}/reset", response_model=QueueStatusResponse)
async def reset_circuit_breaker(service: str, queue_manager: QueueManager = Depends(get_queue_manager)):
    """Reset circuit breaker for a specific service (same as manual resume)."""
    service_enum = ThirdPartyService(service.lower())  # Validate service
    queue_manager.circuit_breaker.manually_resume_service(service_enum)
```

### 3. Circuit Breaker Service Reset
**What happens:** `CircuitBreakerService.manually_reset_circuit()` executes
**Location:** `app/core/circuit_breaker.py` - `manually_resume_service()`
**Timing:** Immediate Redis operation
**Database State:** Redis circuit breaker state updated

```python
def manually_resume_service(self, service: ThirdPartyService) -> None:
    """Manually reset circuit breaker state for a service."""
    key = f"circuit_breaker:{service.value}"
    self.redis_client.hset(key, mapping={
        "state": "closed",
        "failure_count": 0,
        "last_failure_time": "",
        "half_open_attempts": 0
    })
    logger.info(f"Circuit breaker manually reset for {service.value}")
```

### 4. Circuit Breaker State Change
**What happens:** Circuit breaker state changes from OPEN → CLOSED
**Location:** Redis state storage
**Timing:** Immediate (< 1 second)
**Effect:** Service requests will now be allowed through circuit breaker

```bash
# Redis state before reset
circuit_breaker:apollo = {
    "state": "open",
    "failure_count": "5", 
    "last_failure_time": "2024-01-15T10:30:00Z"
}

# Redis state after reset  
circuit_breaker:apollo = {
    "state": "closed",
    "failure_count": "0",
    "last_failure_time": "",
    "half_open_attempts": "0"
}
```

### 5. Queue Status Remains Unchanged
**What happens:** Queue remains PAUSED (circuit breaker reset does NOT resume queue)
**Location:** Redis queue status keys
**Timing:** No change - queue status is independent of circuit breaker
**Database State:** Queue status unchanged in Redis

```bash
# Queue status BEFORE circuit breaker reset
queue_status:apollo = "PAUSED"

# Queue status AFTER circuit breaker reset  
queue_status:apollo = "PAUSED"  # NO CHANGE
```

### 6. Campaign Status Remains Unchanged
**What happens:** Campaigns remain PAUSED (circuit breaker reset does NOT resume campaigns)
**Location:** PostgreSQL campaigns table
**Timing:** No change to campaign status
**Database State:** All campaign statuses remain PAUSED (they were ALL paused when circuit breaker opened)

```sql
-- Campaign status BEFORE circuit breaker reset
SELECT id, status, status_message FROM campaigns WHERE status = 'PAUSED';
-- Results: ALL campaigns with status = 'PAUSED' (system-wide pause on circuit breaker opening)

-- Campaign status AFTER circuit breaker reset
SELECT id, status, status_message FROM campaigns WHERE status = 'PAUSED';  
-- Results: SAME - No campaigns automatically resumed
```

### 7. Job Status Remains Unchanged
**What happens:** Jobs remain PAUSED (no automatic resume cascade)
**Location:** PostgreSQL jobs table  
**Timing:** No change to job status
**Database State:** All job statuses remain PAUSED

```sql
-- Job status distribution BEFORE reset
SELECT status, COUNT(*) FROM jobs GROUP BY status;
-- PAUSED: 150, COMPLETED: 45, FAILED: 5

-- Job status distribution AFTER reset  
SELECT status, COUNT(*) FROM jobs GROUP BY status;
-- PAUSED: 150, COMPLETED: 45, FAILED: 5  -- NO CHANGE
```

### 8. System State Summary
**What happens:** System remains in paused state despite circuit breaker reset
**Final State:**
- Circuit Breaker: CLOSED ✅
- Queue: PAUSED ❌ 
- All Campaigns: PAUSED ❌
- All Jobs: PAUSED ❌

### 9. Frontend Status Update
**What happens:** Frontend updates circuit breaker status display
**Location:** `QueueMonitoringDashboard.tsx` - status refresh after API call
**Timing:** Immediate UI update after successful API response
**User Experience:** Circuit breaker shows as CLOSED, but queue resume button still required

### 10. Manual Queue Resume Required
**What happens:** User must SEPARATELY use "Resume Queue" button to resume operations
**Location:** Same frontend dashboard - Manual Queue Resume section
**Requirement:** This is the ONLY way to resume campaigns and jobs
**User Workflow:** Circuit breaker reset → Manual queue resume (separate action)

## Complete Flow Diagram

```
User Action: "Reset Circuit Breaker" 
    ↓
API Call: POST /circuit-breakers/{service}/reset
    ↓  
Circuit Breaker State: OPEN → CLOSED
    ↓
Queue Status: PAUSED (NO CHANGE)
    ↓
Campaign Status: PAUSED (NO CHANGE)  
    ↓
Job Status: PAUSED (NO CHANGE)
    ↓
Background Tasks: Still suspended (NO CHANGE)
    ↓
Frontend Update: Circuit breaker shows CLOSED
    ↓
User Must Click: "Resume Queue" (SEPARATE ACTION)
```

## Key Separation Principles

### 1. Circuit Breaker vs Campaign State Independence
- **Circuit Breaker:** Service-level failure detection and prevention
- **Campaign State:** Business-level workflow control  
- **Separation:** Circuit breaker reset does NOT affect campaign state

### 2. Manual Control Requirement
- **No Automatic Resume:** Circuit breaker reset intentionally does NOT trigger resume
- **Explicit User Action:** User must explicitly choose to resume operations
- **Predictable Behavior:** No surprising automatic actions

### 3. Prerequisites for Queue Resume
- **Circuit Breaker Reset:** Prerequisite for queue resume (but not sufficient)
- **Manual Queue Resume:** Required separate action after circuit breaker reset
- **Validation:** Queue resume validates ALL circuit breakers are closed

## User Workflow Steps

### Step 1: Identify Open Circuit Breakers
```
Dashboard → Circuit Breaker Status → Identify services showing "OPEN"
```

### Step 2: Reset Each Open Circuit Breaker
```
For each OPEN circuit breaker:
  Click "Reset Circuit Breaker" button → Confirm action → Wait for success message
```

### Step 3: Verify All Circuit Breakers Closed
```
Refresh dashboard → Confirm all circuit breakers show "CLOSED" status
```

### Step 4: Resume Queue (Separate Action)
```
Manual Queue Resume section → Click "Resume Queue & All Campaigns" → Confirm action
```

## API Response Examples

### Successful Circuit Breaker Reset
```json
{
  "status": "success",
  "data": {
    "service": "apollo",
    "action": "circuit_breaker_reset", 
    "message": "Circuit breaker reset for apollo - service manually resumed"
  }
}
```

### Frontend Status After Reset
```typescript
// Circuit breaker status
{
  "apollo": {
    "circuit_state": "closed",    // Changed from "open"
    "queue_paused": true,         // Still paused
    "failure_count": 0,           // Reset to 0
    "failure_threshold": 5
  }
}
```

## Monitoring and Verification

### Log Messages to Monitor
```bash
# Circuit breaker reset
"Circuit breaker manually reset for apollo"

# Queue status check (should still show paused)
"Queue status for apollo: PAUSED"

# Campaign status check (should still show paused campaigns)
"Campaign status check: 5 campaigns remain paused"
```

### Verification Queries

#### Redis Circuit Breaker State
```bash
# Check circuit breaker state after reset
redis-cli HGETALL "circuit_breaker:apollo"
# Expected: state=closed, failure_count=0
```

#### Queue Status (Should Still Be Paused)
```bash
# Check queue status (should remain paused)
redis-cli HGET "queue_status" "apollo"  
# Expected: "PAUSED"
```

#### Campaign Status (Should Still Be Paused)
```sql
-- Check campaign status (should remain paused)
SELECT COUNT(*) FROM campaigns WHERE status = 'PAUSED';
-- Expected: Same count as before reset
```

## Error Handling

### Invalid Service Name
```json
{
  "status": "error",
  "detail": "Invalid service name: invalid_service. Valid services: ['apollo', 'perplexity', 'openai', 'instantly', 'millionverifier']"
}
```

### Circuit Breaker Already Closed
```json
{
  "status": "success",
  "data": {
    "service": "apollo",
    "action": "circuit_breaker_reset",
    "message": "Circuit breaker reset for apollo - service manually resumed"
  }
}
```
*Note: Reset operation is idempotent - always succeeds*

### Redis Connection Error
```json
{
  "status": "error", 
  "detail": "Error resetting circuit breaker: Redis connection failed"
}
```

## Important Notes

### ⚠️ What Circuit Breaker Reset Does NOT Do
- Does NOT resume campaigns
- Does NOT resume jobs  
- Does NOT resume background task processing
- Does NOT unpause queues
- Does NOT trigger any automatic recovery workflows

### ✅ What Circuit Breaker Reset Does Do
- Clears failure count for the specific service
- Changes circuit breaker state from OPEN to CLOSED
- Allows new requests to the service (if system were operational)
- Removes the "circuit breaker open" impediment to queue resume
- Provides clear UI feedback to user

### 🔄 Next Steps After Circuit Breaker Reset
1. **Verify all circuit breakers are closed** (prerequisite check)
2. **Use manual queue resume** (the only way to resume campaigns)
3. **Monitor system recovery** (campaigns and jobs resume through queue resume)

This separation ensures that service recovery and campaign resumption are distinct, controllable operations that prevent unexpected system behavior. 