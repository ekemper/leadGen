import os
import sys
from rq import Worker, Queue, Connection
from redis import Redis
from server.app import create_app
from server.utils.logging_config import worker_logger, combined_logger

def get_redis_connection():
    """Get Redis connection with configuration from environment variables."""
    return Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD'),
        db=int(os.getenv('REDIS_DB', 0))
    )

# Create Flask app context
flask_app = create_app()

# Configure Redis connection
redis_conn = get_redis_connection()

if __name__ == '__main__':
    worker_logger.info("Starting RQ worker...")
    combined_logger.info(
        "Starting RQ worker",
        extra={
            'component': 'worker',
            'redis_config': {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': os.getenv('REDIS_PORT', 6379),
                'db': os.getenv('REDIS_DB', 0)
            }
        }
    )
    
    try:
        with Connection(redis_conn):
            # Create worker with multiple queues
            worker = Worker(
                queues=['default', 'high', 'low'],
                name=f'worker.{os.getpid()}',
                connection=redis_conn
            )
            
            worker_logger.info(
                f"Worker {worker.name} started",
                extra={
                    'worker_name': worker.name,
                    'queues': worker.queues
                }
            )
            combined_logger.info(
                f"Worker {worker.name} started",
                extra={
                    'component': 'worker',
                    'worker_name': worker.name,
                    'queues': worker.queues
                }
            )
            
            worker.work(
                with_scheduler=True,
                burst=False,
                logging_level='INFO'
            )
    except Exception as e:
        worker_logger.error(
            "Worker failed to start",
            extra={
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        combined_logger.error(
            "Worker failed to start",
            extra={
                'component': 'worker',
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        sys.exit(1) 