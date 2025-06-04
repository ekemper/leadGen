# Manual Queue Resume Flow Documentation

## Overview

This document details the complete manual queue resume process, which is the PRIMARY and ONLY way to resume campaigns after circuit breaker events. This process implements prerequisite validation and coordinated system-wide resumption to ensure safe, predictable recovery.

## Flow Sequence

### 1. User Initiates Queue Resume
**What happens:** User clicks "Resume Queue & All Campaigns" button in UI
**Location:** Frontend - `QueueMonitoringDashboard.tsx` - Manual Queue Resume section
**Prerequisites:** User sees "Ready to Resume" state (all circuit breakers closed)
**User Action:** Single button click to trigger system-wide resume

```typescript
// Frontend queue resume trigger
const resumeQueue = async () => {
    const data = await api.post('/queue-management/resume-queue');
    setSuccessMessage(`Successfully resumed queue system. ${data.data?.message || ''}`);
}
```

### 2. API Endpoint Processing
**What happens:** Frontend calls `POST /api/v1/queue-management/resume-queue`
**Location:** `app/api/endpoints/queue_management.py` - `resume_queue()`
**Timing:** Immediate HTTP request processing
**Validation:** Comprehensive prerequisite checks before any resume action

```python
@router.post("/resume-queue", response_model=QueueStatusResponse)
async def resume_queue(queue_manager: QueueManager = Depends(get_queue_manager), db: Session = Depends(get_db)):
    """Manually resume the entire queue system (NEW MANUAL RESUME LOGIC)."""
    logger.info("Manual queue resume requested - validating prerequisites")
```

### 3. Circuit Breaker Prerequisite Validation
**What happens:** API validates ALL circuit breakers are CLOSED (prerequisite check)
**Location:** `resume_queue()` function - STEP 1
**Timing:** Immediate validation before any resume actions
**Failure Mode:** If ANY circuit breaker is open, request fails with error

```python
# STEP 1: Validate ALL circuit breakers are closed (prerequisite check)
blocked_services = []
all_services = [ThirdPartyService.APOLLO, ThirdPartyService.PERPLEXITY, ...]

for service in all_services:
    allowed, reason = circuit_breaker.should_allow_request(service)
    if not allowed:
        blocked_services.append(f"{service.value} ({reason})")

if blocked_services:
    error_message = f"Cannot resume queue: Circuit breakers still open for: {', '.join(blocked_services)}"
    raise HTTPException(status_code=400, detail=error_message)
```

### 4. Prerequisites Met - Resume Proceeding
**What happens:** Prerequisites validated successfully, queue resume begins
**Location:** `resume_queue()` function - STEP 2
**Timing:** Immediate after prerequisite validation
**Logging:** Clear indication that prerequisites are met

```python
logger.info("Prerequisites met: All circuit breakers are closed - proceeding with queue resume")
```

### 5. Service Queue Resumption
**What happens:** Resume queue for ALL services and resume jobs for each service
**Location:** `resume_queue()` function - STEP 2
**Timing:** Sequential processing across all services
**Database State:** Redis queue status updated, job statuses updated

```python
# STEP 2: Resume queue for all services
total_jobs_resumed = 0
for service in all_services:
    # Resume service queues
    circuit_breaker.manually_resume_service(service)
    
    # Resume jobs for each service
    jobs_resumed = queue_manager.resume_jobs_for_service(service)
    total_jobs_resumed += jobs_resumed
    
    logger.info(f"Queue resume: {jobs_resumed} jobs resumed for {service.value}")
```

### 6. Campaign Resumption Coordination
**What happens:** Resume ALL paused campaigns (coordinated resume)
**Location:** `resume_queue()` function - STEP 3
**Timing:** After service queue resumption
**Scope:** ALL paused campaigns in database

```python
# STEP 3: Resume ALL paused campaigns (coordinated resume)
campaign_service = CampaignService()

# Get ALL paused campaigns
paused_campaigns = (
    db.query(Campaign)
    .filter(Campaign.status == CampaignStatus.PAUSED)
    .all()
)

campaigns_resumed = 0
campaign_resume_errors = []

for campaign in paused_campaigns:
    try:
        # Resume the campaign (all prerequisites are met)
        await campaign_service.resume_campaign(campaign.id, db)
        campaigns_resumed += 1
        logger.info(f"Queue resume: Campaign {campaign.id} resumed")
    except Exception as e:
        error_msg = f"Campaign {campaign.id}: {str(e)}"
        campaign_resume_errors.append(error_msg)
        logger.error(f"Error resuming campaign {campaign.id} during queue resume: {str(e)}")
```

### 7. Campaign Status Updates
**What happens:** Campaign status changes from PAUSED → RUNNING for all successfully resumed campaigns
**Location:** `CampaignService.resume_campaign()` method
**Timing:** Within campaign resume transaction
**Database State:** PostgreSQL campaigns table status updated

```sql
-- Campaign status updates during queue resume
UPDATE campaigns 
SET status = 'RUNNING', 
    status_message = 'Campaign resumed - services are available',
    updated_at = NOW()
WHERE id IN (successfully_resumed_campaign_ids);
```

### 8. Job Status Cascade
**What happens:** Campaign resume triggers job resume logic
**Location:** Campaign resume logic cascades to associated jobs
**Timing:** Immediate after campaign status update
**Database State:** Job status changes from PAUSED → PENDING/PROCESSING

```python
# Job resume cascade (handled by campaign resume)
for job in campaign.jobs.filter(status=JobStatus.PAUSED):
    job.status = JobStatus.PENDING  # Reset to pending for reprocessing
    job.error = None  # Clear pause error message
    job.updated_at = datetime.utcnow()
```

### 9. Background Task Resumption
**What happens:** Background tasks resume processing jobs
**Location:** Background task workers detect resumed campaign and job statuses
**Timing:** Immediate for new tasks, gradual for task queue processing
**Effect:** Job processing resumes across all services

```python
# Background tasks detect resumed state
if campaign.status == CampaignStatus.RUNNING and job.status == JobStatus.PENDING:
    # Process job normally - no longer paused
    process_job(job)
```

### 10. Complete Resume Operation Logging
**What happens:** Log the complete queue resume operation results
**Location:** `resume_queue()` function - STEP 4
**Timing:** After all resume operations complete
**Reporting:** Comprehensive success/error reporting

```python
# STEP 4: Log the complete queue resume operation
logger.info(f"Manual queue resume completed: {total_jobs_resumed} jobs, {campaigns_resumed} campaigns resumed")

response_data = {
    "queue_resumed": True,
    "jobs_resumed": total_jobs_resumed,
    "campaigns_eligible": len(paused_campaigns),
    "campaigns_resumed": campaigns_resumed,
    "services_resumed": [service.value for service in all_services],
    "prerequisites_met": "All circuit breakers closed",
    "message": f"Queue resumed successfully: {total_jobs_resumed} jobs and {campaigns_resumed} campaigns resumed"
}
```

### 11. Frontend Status Update
**What happens:** Frontend updates all status displays
**Location:** `QueueMonitoringDashboard.tsx` - automatic refresh after API success
**Timing:** Immediate UI update after successful API response
**User Experience:** System shows as fully operational, all paused states cleared

### 12. System Fully Operational
**What happens:** Complete system state restoration
**Final State:**
- All Circuit Breakers: CLOSED ✅
- Queue: ACTIVE ✅
- All Campaigns: RUNNING ✅ 
- All Jobs: ACTIVE ✅
- Background tasks: Processing ✅

## Complete Flow Diagram

```
User Action: "Resume Queue & All Campaigns"
    ↓
API Call: POST /queue-management/resume-queue
    ↓
Prerequisite Check: ALL circuit breakers must be CLOSED
    ├─ FAIL → Return error "Cannot resume: Circuit breaker {service} is open"
    └─ PASS → Continue to resume
    ↓
Service Queue Resume: For ALL services
    ├─ Redis queue status: PAUSED → ACTIVE
    └─ Jobs: PAUSED → PENDING/PROCESSING
    ↓
Campaign Resume: For ALL paused campaigns
    ├─ Campaign status: PAUSED → RUNNING
    └─ Status message: Updated to "resumed"
    ↓
Job Resume Cascade: Campaign resume triggers job resume
    ├─ Job status: PAUSED → PENDING
    └─ Job errors: Cleared
    ↓
Background Tasks: Resume processing
    └─ Normal job processing workflow resumes
    ↓
Frontend Update: All status displays updated
    └─ System shows as fully operational
```

## Prerequisite Validation Details

### Circuit Breaker Check Logic
```python
# Check each service circuit breaker
all_services = [
    ThirdPartyService.APOLLO,         # Lead fetching
    ThirdPartyService.PERPLEXITY,     # Lead enrichment
    ThirdPartyService.OPENAI,         # Email copy generation
    ThirdPartyService.INSTANTLY,      # Lead creation
    ThirdPartyService.MILLIONVERIFIER # Email verification
]

for service in all_services:
    allowed, reason = circuit_breaker.should_allow_request(service)
    if not allowed:
        # Block resume - return detailed error
        blocked_services.append(f"{service.value} ({reason})")
```

### Error Response for Failed Prerequisites
```json
{
  "status": "error",
  "detail": "Cannot resume queue: Circuit breakers still open for: apollo (open), perplexity (open)"
}
```

### Success Response for Met Prerequisites
```json
{
  "status": "success",
  "data": {
    "queue_resumed": true,
    "jobs_resumed": 45,
    "campaigns_eligible": 8,
    "campaigns_resumed": 8,
    "services_resumed": ["apollo", "perplexity", "openai", "instantly", "millionverifier"],
    "prerequisites_met": "All circuit breakers closed",
    "message": "Queue resumed successfully: 45 jobs and 8 campaigns resumed"
  }
}
```

## Error Handling and Edge Cases

### Campaign Resume Errors
```python
# Individual campaign resume can fail without blocking others
for campaign in paused_campaigns:
    try:
        await campaign_service.resume_campaign(campaign.id, db)
        campaigns_resumed += 1
    except Exception as e:
        # Log error but continue with other campaigns
        campaign_resume_errors.append(f"Campaign {campaign.id}: {str(e)}")
        logger.error(f"Error resuming campaign {campaign.id}: {str(e)}")
```

### Partial Resume Response
```json
{
  "status": "success",
  "data": {
    "queue_resumed": true,
    "jobs_resumed": 45,
    "campaigns_eligible": 8,
    "campaigns_resumed": 6,
    "campaign_resume_errors": [
      "Campaign 12345: Invalid campaign state transition",
      "Campaign 67890: Database constraint violation"
    ],
    "message": "Queue resumed successfully: 45 jobs and 6 campaigns resumed (with 2 campaign errors)"
  }
}
```

### Database Transaction Safety
```python
# Each campaign resume is wrapped in its own transaction
for campaign in paused_campaigns:
    try:
        # Atomic campaign resume operation
        with db.begin():  # Transaction boundary
            await campaign_service.resume_campaign(campaign.id, db)
            campaigns_resumed += 1
    except Exception as e:
        # Transaction rolled back automatically
        # Other campaigns not affected
        campaign_resume_errors.append(error_msg)
```

## User Experience Flow

### Before Queue Resume
```
Dashboard shows:
- Circuit Breakers: Some OPEN (red)
- Manual Queue Resume: "⚠️ Cannot Resume Queue" (blocked)
- Required Action: Reset open circuit breakers first
```

### After Circuit Breaker Reset
```
Dashboard shows:
- Circuit Breakers: All CLOSED (green)
- Manual Queue Resume: "✅ Ready to Resume" (enabled)
- Available Action: "Resume Queue & All Campaigns" button
```

### During Queue Resume
```
Dashboard shows:
- Button: "Resuming Queue..." (disabled, loading state)
- Progress: API call in progress
- Status: Waiting for response
```

### After Successful Queue Resume
```
Dashboard shows:
- Success Message: "Successfully resumed queue system..."
- Circuit Breakers: All CLOSED (green)
- Campaigns: Status updated to RUNNING
- Jobs: Resume processing
- Background Tasks: Active
```

## Monitoring and Verification

### Log Messages to Monitor
```bash
# Queue resume initiation
"Manual queue resume requested - validating prerequisites"

# Prerequisites validation
"Prerequisites met: All circuit breakers are closed - proceeding with queue resume"

# Service resume
"Queue resume: 15 jobs resumed for apollo"

# Campaign resume
"Queue resume: Campaign 12345 resumed"

# Completion
"Manual queue resume completed: 45 jobs, 8 campaigns resumed"
```

### Database State Verification

#### Check Campaign Status After Resume
```sql
-- Verify campaigns are resumed
SELECT status, COUNT(*) FROM campaigns GROUP BY status;
-- Expected: PAUSED count decreased, RUNNING count increased

-- Check specific resume messages
SELECT id, name, status_message FROM campaigns 
WHERE status = 'RUNNING' AND status_message LIKE '%resumed%';
```

#### Check Job Status After Resume
```sql
-- Verify jobs are resumed
SELECT status, COUNT(*) FROM jobs GROUP BY status;
-- Expected: PAUSED count decreased, PENDING/PROCESSING count increased

-- Check job error clearing
SELECT COUNT(*) FROM jobs WHERE status != 'PAUSED' AND error IS NULL;
```

### Redis State Verification
```bash
# Check queue status (should be active)
redis-cli HGETALL "queue_status"
# Expected: All services showing "ACTIVE"

# Check circuit breaker status (should be closed)
redis-cli HGETALL "circuit_breaker:apollo"
# Expected: state=closed, failure_count=0
```

## Important Notes

### 🎯 This is the ONLY Way to Resume Campaigns
- Manual queue resume is the EXCLUSIVE method for campaign resumption
- No other action (circuit breaker reset, individual campaign actions) resumes campaigns
- This ensures predictable, controlled recovery after service failures

### ✅ Prerequisites are Mandatory
- ALL circuit breakers must be closed before queue resume
- No partial resume - either all prerequisites met or operation fails
- Clear error messages guide user through prerequisite resolution

### 🔄 Coordinated System Resume
- Queue resume triggers cascade: Queue → Campaigns → Jobs → Background Tasks
- All components resume together for consistent system state
- Database transactions ensure atomic updates where possible

### 📊 Comprehensive Reporting
- Detailed success/error reporting for transparency
- Individual campaign failures don't block overall operation
- Clear metrics on what was resumed vs what had errors

### 🚀 Immediate Effect
- Background tasks resume processing immediately after successful queue resume
- Job processing resumes for all services simultaneously
- System returns to full operational state

This manual queue resume process provides the controlled, predictable recovery mechanism that replaces all previous automatic resume logic, ensuring users have full control over when and how the system recovers from service failures. 