import os
import sys
import signal
from datetime import datetime
from rq import Worker, Connection
from rq.worker import StopRequested
from server.app import create_app
from server.utils.logging_config import worker_logger
from server.config.queue_config import get_redis_connection, QUEUE_CONFIG

# Create Flask app context
flask_app = create_app()

# Configure Redis connection
redis_conn = get_redis_connection()

def handle_sigterm(signum, frame):
    """Handle SIGTERM signal gracefully."""
    worker_logger.info("Received SIGTERM signal, shutting down gracefully...")
    worker_logger.info(
        "Received SIGTERM signal, shutting down gracefully...",
        extra={'component': 'worker', 'signal': 'SIGTERM'}
    )
    raise StopRequested()

def handle_sigint(signum, frame):
    """Handle SIGINT signal gracefully."""
    worker_logger.info("Received SIGINT signal, shutting down gracefully...")
    worker_logger.info(
        "Received SIGINT signal, shutting down gracefully...",
        extra={'component': 'worker', 'signal': 'SIGINT'}
    )
    raise StopRequested()

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigint)

    worker_logger.info("Starting RQ worker...")
    worker_logger.info(
        "Starting RQ worker",
        extra={
            'component': 'worker',
            'redis_config': {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': os.getenv('REDIS_PORT', 6379),
                'db': os.getenv('REDIS_DB', 0)
            },
            'queue_config': QUEUE_CONFIG,
            'start_time': datetime.utcnow().isoformat()
        }
    )
    
    try:
        with Connection(redis_conn):
            # Create worker with default queue
            worker = Worker(
                queues=['default'],
                name=f'worker.{os.getpid()}',
                connection=redis_conn,
                default_worker_ttl=QUEUE_CONFIG['default']['timeout'],
                default_result_ttl=QUEUE_CONFIG['default']['job_timeout']
            )
            
            worker_logger.info(
                f"Worker {worker.name} started",
                extra={
                    'worker_name': worker.name,
                    'queues': worker.queues,
                    'queue_config': QUEUE_CONFIG,
                    'pid': os.getpid(),
                    'start_time': datetime.utcnow().isoformat()
                }
            )
            
            # Start worker with supported configuration
            worker.work(
                with_scheduler=True,
                burst=False,
                logging_level='INFO'
            )
    except StopRequested:
        worker_logger.info("Worker stopped gracefully")
        worker_logger.info(
            "Worker stopped gracefully",
            extra={'component': 'worker', 'stop_time': datetime.utcnow().isoformat()}
        )
        sys.exit(0)
    except Exception as e:
        worker_logger.error(
            "Worker failed to start",
            extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': sys.exc_info()
            }
        )
        worker_logger.error(
            "Worker failed to start",
            extra={
                'component': 'worker',
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': sys.exc_info()
            }
        )
        sys.exit(1) 