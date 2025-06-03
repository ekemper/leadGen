# API Integration Rate Limiter

## Overview

The `ApiIntegrationRateLimiter` is a distributed, Redis-backed rate limiter designed to control outgoing API calls from this service to third-party APIs. It is configurable per API and ensures that your service does not exceed the rate limits imposed by external providers, preventing IP bans and service disruptions.

## Rationale
- **Protects against API bans** by enforcing rate limits for each integration.
- **Distributed and robust**: Works across multiple processes and servers using Redis.
- **Configurable**: Each API can have its own rate limit settings.
- **Integrates with job status logic**: Jobs that exceed the rate limit are marked as `DELAYED` and requeued with a reason.

## Usage

### 1. Configuration
Define per-API rate limits in your service file:
```python
API_RATE_LIMITS = {
    'MillionVerifier': {'max_requests': 60, 'period_seconds': 60},
    'Instantly': {'max_requests': 100, 'period_seconds': 60},
    # Add more APIs as needed
}
```

### 2. Initialization
```python
from server.utils.api_integration_rate_limiter import ApiIntegrationRateLimiter
redis_client = get_redis_connection()
limiter = ApiIntegrationRateLimiter(redis_client, 'MillionVerifier', 60, 60)
```

### 3. Acquiring a Slot
```python
if limiter.acquire():
    # Proceed with API call
else:
    # Set job status to DELAYED, set delay_reason, and requeue
```

### 4. Integration with Job Logic
- If a job cannot acquire a slot, set its status to `DELAYED` and provide a `delay_reason` (e.g., rate limit hit or API key error).
- Requeue the job after a delay.

## Example
```python
limiter_cfg = API_RATE_LIMITS['MillionVerifier']
limiter = ApiIntegrationRateLimiter(redis_client, 'MillionVerifier', limiter_cfg['max_requests'], limiter_cfg['period_seconds'])
if not limiter.acquire():
    job.status = JobStatus.DELAYED
    job.delay_reason = 'Rate limit exceeded for MillionVerifier'
    db.session.commit()
    queue.enqueue_in(timedelta(seconds=10), verify_email, job_id, email, api_key)
    return
# Proceed with API call
```

## Extension
- Add new APIs by updating the `API_RATE_LIMITS` dictionary.
- The class can be extended to support more advanced rate limiting strategies (e.g., leaky bucket, sliding window).

## Error Handling
- Handles Redis connection errors gracefully.
- Integrate with job error handling for API key errors and other retryable failures.

## File Location
- Implementation: `server/utils/api_integration_rate_limiter.py`
- Used in: `server/background_services/email_verifier_service.py`, `instantly_service.py`, etc.

---
For questions or improvements, see the code comments or contact the backend maintainers. 