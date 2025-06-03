from celery import Celery
from app.core.config import settings

# Initialize centralized logging for workers
from app.core.logging_config import init_logging
from app.core.logger import get_logger
import logging

# Initialize logging system for workers
init_logging()
logger = get_logger(__name__)

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks", "app.workers.campaign_tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Configure Celery's internal logging to use our centralized system
celery_app.conf.update(
    worker_hijack_root_logger=False,  # Don't let Celery hijack root logger
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)

# Ensure Celery loggers use our handlers
celery_logger = logging.getLogger('celery')
celery_task_logger = logging.getLogger('celery.task')
celery_worker_logger = logging.getLogger('celery.worker')

# Set appropriate log levels for Celery components
celery_logger.setLevel(logging.INFO)
celery_task_logger.setLevel(logging.INFO)
celery_worker_logger.setLevel(logging.INFO)

# Worker lifecycle signals
from celery.signals import worker_ready, worker_shutdown, task_prerun, task_postrun, task_failure

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Log when worker is ready to accept tasks."""
    logger.info("Celery worker ready to accept tasks", extra={
        "component": "worker",
        "worker_pid": sender.pid if sender else "unknown",
        "event": "worker_ready"
    })

@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Log when worker is shutting down."""
    logger.info("Celery worker shutting down", extra={
        "component": "worker",
        "worker_pid": sender.pid if sender else "unknown",
        "event": "worker_shutdown"
    })

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log before task execution."""
    logger.info(f"Starting task: {task.name}", extra={
        "component": "worker",
        "task_id": task_id,
        "task_name": task.name,
        "event": "task_start"
    })

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Log after task execution."""
    logger.info(f"Completed task: {task.name}", extra={
        "component": "worker",
        "task_id": task_id,
        "task_name": task.name,
        "state": state,
        "event": "task_complete"
    })

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Log task failures."""
    logger.error(f"Task failed: {sender.name}", extra={
        "component": "worker",
        "task_id": task_id,
        "task_name": sender.name,
        "error": str(exception),
        "event": "task_failure"
    }, exc_info=einfo)

# Log worker initialization
logger.info("Celery worker initialized with centralized logging", extra={
    "component": "worker",
    "broker": settings.CELERY_BROKER_URL,
    "backend": settings.CELERY_RESULT_BACKEND
}) 