# RQ (Redis Queue) Implementation Improvements

## Current Implementation Overview

The system currently uses RQ for handling background tasks with a chain of 4 sequential tasks:
1. `fetch_and_save_leads_task`
2. `email_verification_task`
3. `enriching_leads_task`
4. `email_copy_generation_task`

## Recommended Improvements

### 1. Error Handling
Current implementation lacks comprehensive error handling in tasks.

**Recommendation:**
```python
def fetch_and_save_leads_task(params, campaign_id):
    with flask_app.app_context():
        try:
            print("RQ job started with:", params, campaign_id)
            ApolloService().fetch_leads(params, campaign_id)
            return {'campaign_id': campaign_id, 'status': 'success'}
        except Exception as e:
            logger.error(f"Error in fetch_and_save_leads_task: {str(e)}")
            # Update campaign status to failed
            with flask_app.app_context():
                campaign = Campaign.query.get(campaign_id)
                if campaign:
                    campaign.status = 'failed'
                    db.session.commit()
            raise
```

### 2. Job Status Tracking
Currently lacks job status monitoring.

**Recommendation:**
```python
def start_campaign(self, campaign_id, params):
    try:
        campaign = Campaign.query.get(campaign_id)
        campaign.status = 'starting'
        campaign.job_status = {
            'fetch_leads': 'pending',
            'email_verification': 'pending',
            'enriching': 'pending',
            'email_copy': 'pending'
        }
        db.session.commit()
        
        # Enqueue jobs with status updates
        job1 = enqueue_fetch_and_save_leads(params, campaign.id)
        campaign.job_ids = {'fetch_leads': job1.id}
        db.session.commit()
```

### 3. Queue Configuration
Missing queue configuration options.

**Recommendation:**
```python
# In tasks.py
rq_queue = Queue(
    name='default',
    connection=redis_conn,
    default_timeout=3600,  # 1 hour timeout
    job_timeout=1800      # 30 minutes per job
)
```

### 4. Worker Management
Current worker implementation is basic.

**Recommendation:**
```python
# In run_worker.py
import os
from rq import Worker, Queue, Connection
from redis import Redis
from server.app import create_app
from rq.worker import HerokuWorker as Worker

def get_redis_connection():
    return Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD'),
        db=int(os.getenv('REDIS_DB', 0))
    )

flask_app = create_app()

if __name__ == '__main__':
    with Connection(get_redis_connection()):
        worker = Worker(
            queues=['default', 'high', 'low'],
            name=os.getenv('WORKER_NAME', 'worker.{}'.format(os.getpid())),
            connection=get_redis_connection()
        )
        worker.work(
            with_scheduler=True,
            burst=False,
            logging_level='INFO'
        )
```

### 5. Job Result Storage
Currently not storing job results.

**Recommendation:**
```python
# In tasks.py
from rq.registry import FinishedJobRegistry, FailedJobRegistry

def get_job_results(campaign_id):
    registry = FinishedJobRegistry(queue=rq_queue)
    failed_registry = FailedJobRegistry(queue=rq_queue)
    
    results = {
        'completed': [job.id for job in registry.get_job_ids()],
        'failed': [job.id for job in failed_registry.get_job_ids()]
    }
    return results
```

### 6. Monitoring and Cleanup
Missing job cleanup and monitoring.

**Recommendation:**
```python
def cleanup_old_jobs(days=7):
    """Clean up jobs older than specified days"""
    registry = FinishedJobRegistry(queue=rq_queue)
    failed_registry = FailedJobRegistry(queue=rq_queue)
    
    cutoff = datetime.now() - timedelta(days=days)
    
    for job_id in registry.get_job_ids():
        job = rq_queue.fetch_job(job_id)
        if job and job.ended_at < cutoff:
            job.delete()
```

### 7. Campaign Status Updates
Add campaign status updates after each task.

**Recommendation:**
```python
def update_campaign_status(campaign_id, status, message=None):
    with flask_app.app_context():
        campaign = Campaign.query.get(campaign_id)
        if campaign:
            campaign.status = status
            if message:
                campaign.status_message = message
            db.session.commit()
```

## Implementation Priority

1. Error Handling - Critical for system stability
2. Job Status Tracking - Essential for user feedback
3. Queue Configuration - Important for performance
4. Campaign Status Updates - Important for user experience
5. Worker Management - Important for scalability
6. Job Result Storage - Useful for debugging
7. Monitoring and Cleanup - Important for maintenance

## Next Steps

1. Implement error handling and job status tracking first
2. Add queue configuration and campaign status updates
3. Enhance worker management
4. Add job result storage
5. Implement monitoring and cleanup utilities

## Additional Considerations

- Add logging throughout the task chain
- Implement retry mechanisms for failed tasks
- Add monitoring dashboard
- Set up alerts for failed jobs
- Consider implementing job prioritization
- Add job progress tracking
- Implement job cancellation mechanism 