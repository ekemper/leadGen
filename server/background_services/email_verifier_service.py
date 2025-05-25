import os
import requests
from server.models import Campaign, Lead
from server.config.database import db
from server.utils.logging_config import app_logger
from server.models.campaign import CampaignStatus
from typing import Dict, Any, List
from server.utils.api_integration_rate_limiter import ApiIntegrationRateLimiter
from server.config.queue_config import get_redis_connection, get_queue
from server.models.job_status import JobStatus
from server.models.job import Job
import time
from datetime import datetime

# Configurable per-API rate limits
API_RATE_LIMITS = {
    'MillionVerifier': {'max_requests': 2, 'period_seconds': 10},
    # Add other APIs here
}

class EmailVerifierService:
    """Service for verifying emails using MillionVerifier API."""

    def __init__(self):
        self.api_key = os.getenv('MILLIONVERIFIER_API_KEY')
        if not self.api_key:
            raise ValueError("MILLIONVERIFIER_API_KEY environment variable is not set")
        self.base_url = "https://api.millionverifier.com/api/v3/"
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def verify_email(self, job_id, email, api_key):
        redis_client = get_redis_connection()
        queue = get_queue()
        limiter_cfg = API_RATE_LIMITS['MillionVerifier']
        limiter = ApiIntegrationRateLimiter(redis_client, 'MillionVerifier', limiter_cfg['max_requests'], limiter_cfg['period_seconds'])
        job = Job.query.get(job_id)
        if not job:
            # handle missing job
            return
        # Try to acquire a rate limit slot
        if not limiter.acquire(block=False):
            job.status = JobStatus.DELAYED.value
            job.delay_reason = 'Rate limit exceeded for MillionVerifier API'
            job.updated_at = datetime.utcnow()
            Job.query.session.commit()
            # Requeue after delay (e.g., 10 seconds)
            queue.enqueue_in(time.timedelta(seconds=10), self.verify_email, job_id, email, api_key)
            return
        try:
            response = requests.get(
                f"{self.base_url}?api={api_key}&email={email}"
            )
            response.raise_for_status()
            if response.json().get('error') == 'API_KEY_INVALID':
                job.status = JobStatus.DELAYED.value
                job.delay_reason = 'API key invalid for MillionVerifier'
                job.updated_at = datetime.utcnow()
                Job.query.session.commit()
                # Requeue after delay (e.g., 60 seconds)
                queue.enqueue_in(time.timedelta(seconds=60), self.verify_email, job_id, email, api_key)
                return
            return response.json()
        except Exception as e:
            app_logger.error(f"Error verifying email {email}: {str(e)}", extra={'component': 'server'})
            return {
                'status': 'error',
                'error': str(e)
            }

