# Service Error → System Pause Flow Documentation

## Overview

This document provides comprehensive documentation of the complete flow from a third-party service error to full system pause. This flow is designed to automatically protect the system from cascading failures while providing clear manual recovery paths.

## Flow Sequence

### 1. Service Error Detection
**What happens:** Third-party service (Apollo/Perplexity/OpenAI/Instantly/MillionVerifier) throws an error
**Location:** Service wrapper classes in `app/background_services/`
**Timing:** Immediate when service request fails

```
Service Request → Exception/Error Response → Error Captured by Service Wrapper
```

### 2. Circuit Breaker Failure Recording
**What happens:** Error captured by service wrapper → Circuit breaker records failure
**Location:** `app/core/circuit_breaker.py` - `CircuitBreakerService.record_failure()`
**Timing:** Immediate after error capture
**Database State:** Redis key updated with failure count

```python
# Example error recording
circuit_breaker.record_failure(
    service=ThirdPartyService.APOLLO,
    error="Request timeout",
    failure_type="timeout"
)
```

### 3. Circuit Breaker Threshold Check
**What happens:** Circuit breaker checks if failure count reaches threshold
**Location:** `CircuitBreakerService.should_allow_request()`
**Timing:** Immediate after failure recording
**Threshold:** Configurable per service (default: 5 failures)

```
if failure_count >= failure_threshold:
    circuit_state = CLOSED → OPEN
```

### 4. Queue Pause Trigger
**What happens:** Circuit breaker opening triggers `_pause_service_queues()`
**Location:** `app/core/queue_manager.py` - `QueueManager._pause_service_queues()`
**Timing:** Immediate when circuit breaker state changes to OPEN
**Database State:** Queue status set to PAUSED in Redis

```python
# Automatic queue pause when circuit breaker opens
def _pause_service_queues(self, service: ThirdPartyService):
    logger.info(f"Pausing queues for service {service.value} due to circuit breaker")
    # Set queue pause state in Redis
    self.redis_client.hset("queue_status", service.value, "PAUSED")
```

### 5. Campaign Event Handler Trigger
**What happens:** Queue pause triggers `campaign_event_handler.handle_circuit_breaker_opened()`
**Location:** `app/services/campaign_event_handler.py`
**Timing:** Immediate after queue pause
**Scope:** ALL running campaigns evaluated for pause

```python
# Event handler processes circuit breaker opening
def handle_circuit_breaker_opened(self, service: ThirdPartyService):
    # Evaluate ALL running campaigns and pause if affected
    campaigns_paused = self.pause_affected_campaigns(service)
```

### 6. Campaign Status Evaluation
**What happens:** Campaign event handler evaluates ALL running campaigns
**Location:** `app/services/campaign_status_monitor.py` - `evaluate_campaign_status_for_service()`
**Timing:** Within seconds of circuit breaker opening
**Logic:** ANY circuit breaker opening immediately pauses ALL running campaigns

```python
# Campaign evaluation logic - SIMPLIFIED
logger.info(f"Circuit breaker opened for {service.value} - pausing ALL running campaigns immediately")
# Pause ALL running campaigns - no dependency checking, no thresholds
for campaign in running_campaigns:
    reason = f"System pause: {service.value} circuit breaker opened"
    campaign.pause(reason)
```

### 7. Campaign Status Update
**What happens:** ALL affected campaigns status changes from RUNNING → PAUSED
**Location:** `app/models/campaign.py` - `Campaign.pause()`
**Timing:** Within the same transaction as evaluation
**Database State:** Campaign status and status_message updated in PostgreSQL

```sql
UPDATE campaigns 
SET status = 'PAUSED', 
    status_message = 'Service apollo circuit breaker opened',
    updated_at = NOW()
WHERE id IN (affected_campaign_ids);
```

### 8. Job Status Propagation
**What happens:** Campaign pause propagates to jobs → ALL jobs paused
**Location:** Background task workers in `app/workers/campaign_tasks.py`
**Timing:** As jobs are processed (immediate for new jobs, gradual for running jobs)
**Database State:** Job status changes from PENDING/PROCESSING → PAUSED

```python
# Job status check in background tasks
if campaign.status == CampaignStatus.PAUSED:
    job.status = JobStatus.PAUSED
    job.error = f"Job paused: Campaign {campaign_id} is paused"
```

### 9. Background Task Suspension
**What happens:** Background tasks stop processing due to paused state
**Location:** All task workers respect campaign and job pause states
**Timing:** Immediate for new tasks, existing tasks complete their current operation
**Effect:** No new job processing begins

### 10. Frontend Status Update
**What happens:** Frontend shows circuit breaker status and manual resume requirement
**Location:** `frontend/src/components/monitoring/QueueMonitoringDashboard.tsx`
**Timing:** Next UI refresh (30-second intervals or manual refresh)
**User Experience:** Clear indication of system pause and required manual action

## Final System State

After the complete cascade:
- **Circuit Breaker:** OPEN
- **Queue:** PAUSED  
- **All Campaigns:** PAUSED (status = 'PAUSED')
- **All Jobs:** PAUSED (status = 'PAUSED')
- **Background Tasks:** Suspended (not processing new work)
- **Frontend:** Shows pause state and manual resume requirement

## Error Propagation Timing

| Step | Component | Timing | Duration |
|------|-----------|--------|----------|
| 1 | Service Error | Immediate | < 1 second |
| 2 | Circuit Breaker | Immediate | < 1 second |
| 3 | Threshold Check | Immediate | < 1 second |
| 4 | Queue Pause | Immediate | < 1 second |
| 5 | Event Handler | Immediate | < 2 seconds |
| 6 | Campaign Evaluation | Database query | 2-5 seconds |
| 7 | Campaign Update | Database transaction | 1-2 seconds |
| 8 | Job Propagation | Gradual | 30 seconds - 2 minutes |
| 9 | Task Suspension | Gradual | 30 seconds - 2 minutes |
| 10 | Frontend Update | Polling interval | Up to 30 seconds |

**Total cascade time:** 5-10 seconds for critical components, full propagation within 2-3 minutes

## Monitoring and Logging

### Log Messages to Monitor

```bash
# Circuit breaker opening
"Circuit breaker opened for service apollo after 5 failures"

# Queue pause
"Pausing queues for service apollo due to circuit breaker"

# Campaign evaluation
"Evaluating campaigns for service apollo failure - 3 campaigns affected"

# Campaign pause
"Campaign 12345 paused due to apollo circuit breaker opened"

# Job pause
"Job 67890 paused: Campaign 12345 is paused"
```

### Database State Queries

```sql
-- Check campaign states
SELECT status, COUNT(*) FROM campaigns GROUP BY status;

-- Check job states  
SELECT status, COUNT(*) FROM jobs GROUP BY status;

-- Check paused campaigns with reasons
SELECT id, name, status_message FROM campaigns WHERE status = 'PAUSED';
```

### Redis State Queries

```bash
# Check circuit breaker states
redis-cli HGETALL "circuit_breaker:apollo"

# Check queue states
redis-cli HGETALL "queue_status"
```

## Recovery Requirements

The system does NOT automatically recover from this state. Manual intervention is required:

1. **Circuit Breaker Reset** - Manual reset of circuit breaker (does NOT resume campaigns)
2. **Manual Queue Resume** - Only way to resume campaigns and jobs
3. **Prerequisite Validation** - ALL circuit breakers must be closed before queue resume

See [MANUAL_CIRCUIT_BREAKER_RESET_FLOW.md](MANUAL_CIRCUIT_BREAKER_RESET_FLOW.md) and [MANUAL_QUEUE_RESUME_FLOW.md](MANUAL_QUEUE_RESUME_FLOW.md) for recovery procedures.

## Technical Implementation Notes

### Circuit Breaker Configuration
- **Failure Threshold:** 5 failures (configurable)
- **Reset Timeout:** 60 seconds for half-open attempts
- **Storage:** Redis with TTL-based recovery tracking

### Campaign Evaluation Logic
- **Threshold:** NO thresholds - ANY circuit breaker opening pauses ALL campaigns
- **Scope:** ALL running campaigns paused immediately regardless of dependencies
- **Transaction Safety:** Database transactions ensure consistency

### Error Handling
- **Failed Evaluations:** Logged but don't block other campaigns
- **Database Errors:** Rollback ensures no partial state updates
- **Redis Failures:** Circuit breaker defaults to OPEN (fail-safe)

### Performance Considerations
- **Batch Operations:** Campaign evaluations use efficient database queries
- **Async Processing:** Event handlers don't block main request flow  
- **Rate Limiting:** Circuit breaker prevents overwhelming failed services

This flow ensures that service failures are contained quickly while providing clear paths for manual recovery once issues are resolved. 