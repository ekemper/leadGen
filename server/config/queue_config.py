import os
from redis import Redis
from rq import Queue

def get_redis_connection():
    """Get Redis connection with configuration from environment variables."""
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        return Redis.from_url(redis_url, ssl_cert_reqs='none')
    # Fallback for local development only
    return Redis.from_url('redis://localhost:6379/0')

# Queue configuration
QUEUE_CONFIG = {
    'default': {
        'name': 'default',
        'timeout': 3600,  # 1 hour queue timeout
        'job_timeout': 1800,  # 30 minutes per job
        'retry_after': 300,  # 5 minutes before retry
        'max_retries': 3,
        'result_ttl': 3600,  # 1 hour result TTL
        'failure_ttl': 3600  # 1 hour failure TTL
    }
}

# Initialize queue
redis_conn = get_redis_connection()
queue = Queue(
    name=QUEUE_CONFIG['default']['name'],
    connection=redis_conn,
    default_timeout=QUEUE_CONFIG['default']['timeout'],
    job_timeout=QUEUE_CONFIG['default']['job_timeout']
)

def get_queue():
    """Get the default queue."""
    return queue 