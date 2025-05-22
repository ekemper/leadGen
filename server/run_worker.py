from rq import Worker, Queue, Connection
from server.config.queue_config import get_redis_conn
from server.utils.logging_config import setup_logger, ContextLogger

# Configure module logger
logger = setup_logger('worker')

def run_worker():
    """Run the RQ worker process."""
    with ContextLogger(logger):
        try:
            redis_conn = get_redis_conn()
            with Connection(redis_conn):
                worker = Worker(['default'])
                logger.info("Starting worker", extra={
                    'metadata': {
                        'queues': worker.queues,
                        'name': worker.name
                    }
                })
                worker.work()
        except Exception as e:
            logger.error(f"Worker error: {str(e)}", exc_info=True)

if __name__ == '__main__':
    run_worker()

# The worker process uses a module-specific logger that writes to /app/logs/combined.log as configured in logging_config.py
# No further changes needed here for logging destination. 