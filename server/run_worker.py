import os
import sys
import signal
import traceback
from datetime import datetime
from rq import Worker
from rq.worker import StopRequested
from server.app import create_app
from server.utils.logging_config import worker_logger
from server.config.queue_config import get_redis_connection, QUEUE_CONFIG

# --- EARLY LOGGING ---
worker_logger.info("run_worker.py script started")
worker_logger.info(
    "Environment variables at startup",
    extra={
        'REDIS_HOST': os.getenv('REDIS_HOST'),
        'REDIS_PORT': os.getenv('REDIS_PORT'),
        'REDIS_DB': os.getenv('REDIS_DB'),
        'FLASK_ENV': os.getenv('FLASK_ENV'),
        'PYTHONPATH': os.getenv('PYTHONPATH'),
        'PATH': os.getenv('PATH'),
    }
)

# --- APP CREATION ---
worker_logger.info("Creating Flask app context...")
try:
    flask_app = create_app()
    worker_logger.info("Flask app context created successfully.")
except Exception as e:
    worker_logger.error(
        "Failed to create Flask app context",
        extra={
            'error': str(e),
            'traceback': traceback.format_exc()
        }
    )
    sys.exit(1)

# --- REDIS CONNECTION ---
worker_logger.info("Configuring Redis connection...")
try:
    redis_conn = get_redis_connection()
    worker_logger.info("Redis connection established.")
except Exception as e:
    worker_logger.error(
        "Failed to connect to Redis",
        extra={
            'error': str(e),
            'traceback': traceback.format_exc()
        }
    )
    sys.exit(1)

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
    worker_logger.info("Registering signal handlers for SIGTERM and SIGINT...")
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigint)
    worker_logger.info("Signal handlers registered.")

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
        worker_logger.info("Instantiating RQ Worker...")
        worker = Worker(
            queues=['default'],
            name=f'worker.{os.getpid()}',
            connection=redis_conn,
            default_worker_ttl=QUEUE_CONFIG['default']['timeout'],
            default_result_ttl=QUEUE_CONFIG['default']['job_timeout']
        )
        worker_logger.info(
            f"Worker {worker.name} instantiated.",
            extra={
                'worker_name': worker.name,
                'queues': worker.queues,
                'queue_config': QUEUE_CONFIG,
                'pid': os.getpid(),
                'start_time': datetime.utcnow().isoformat()
            }
        )
        worker_logger.info("Worker entering work loop...")
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
                'traceback': traceback.format_exc()
            }
        )
        worker_logger.error(
            "Worker failed to start",
            extra={
                'component': 'worker',
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc()
            }
        )
        sys.exit(1) 