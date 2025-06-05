from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import Depends
from redis import Redis

from app.core.logger import get_logger
from app.core.circuit_breaker import CircuitBreakerService, ThirdPartyService, get_circuit_breaker
from app.models.job import Job, JobStatus, JobType
from app.models.lead import Lead
from app.core.config import get_redis_connection
from app.core.database import get_db

logger = get_logger(__name__)

class QueueManager:
    """
    Simplified queue manager with global circuit breaker integration.
    
    Features:
    - Global circuit breaker state checking
    - Pause/resume all jobs on circuit breaker state changes
    - No service-specific job dependencies
    - Celery task creation for resumed jobs
    """
    
    def __init__(self, redis_client=None, db: Optional[Session] = None):
        """
        Initialize QueueManager with optional dependencies.
        
        Args:
            redis_client: Redis client for queue operations
            db: Database session (optional)
        """
        self.redis_client = redis_client
        self.db = db
        self.circuit_breaker = get_circuit_breaker(redis_client=redis_client)
    
    def should_process_job(self) -> bool:
        """
        Check if jobs should be processed based on global circuit breaker status.
        Simplified: only check global circuit state, not service-specific.
        """
        try:
            return self.circuit_breaker.should_allow_request()
        except Exception as e:
            logger.error(f"Error checking if should process job: {e}")
            # Fail safe - allow processing if we can't determine state
            return True

    def pause_all_jobs_on_breaker_open(self, reason: str) -> int:
        """
        Pause all PENDING and PROCESSING jobs when circuit breaker opens.
        Simplified: affect all active jobs regardless of type or service dependency.
        
        Returns:
            int: Number of jobs paused
        """
        try:
            if not self.db:
                from app.core.database import SessionLocal
                db = SessionLocal()
                should_close = True
            else:
                db = self.db
                should_close = False
            
            try:
                # Find all active jobs (PENDING or PROCESSING)
                active_jobs = (
                    db.query(Job)
                    .filter(
                        Job.status.in_([JobStatus.PENDING, JobStatus.PROCESSING])
                    )
                    .all()
                )
                
                paused_count = 0
                for job in active_jobs:
                    job.status = JobStatus.PAUSED
                    job.error = f"Paused due to circuit breaker open: {reason}"
                    job.updated_at = datetime.utcnow()
                    paused_count += 1
                    
                    logger.info(f"Paused job {job.id} ({job.job_type}) due to circuit breaker")
                
                db.commit()
                
                logger.warning(f"Paused {paused_count} jobs due to circuit breaker opening: {reason}")
                return paused_count
                
            finally:
                if should_close:
                    db.close()
                    
        except Exception as e:
            logger.error(f"Error pausing jobs on circuit breaker open: {e}")
            if self.db:
                self.db.rollback()
            return 0

    def resume_all_jobs_on_breaker_close(self) -> int:
        """
        Resume all PAUSED jobs when circuit breaker closes.
        Creates new celery tasks for each resumed job.
        
        Returns:
            int: Number of jobs resumed
        """
        try:
            if not self.db:
                from app.core.database import SessionLocal
                db = SessionLocal()
                should_close = True
            else:
                db = self.db
                should_close = False
            
            try:
                # Find all paused jobs
                paused_jobs = (
                    db.query(Job)
                    .filter(Job.status == JobStatus.PAUSED)
                    .all()
                )
                
                resumed_count = 0
                for job in paused_jobs:
                    try:
                        # Resume job to PENDING status
                        job.status = JobStatus.PENDING
                        job.error = None  # Clear the pause error
                        job.updated_at = datetime.utcnow()
                        
                        # Create new celery task for resumed job
                        new_task_id = self._create_celery_task_for_job(job)
                        if new_task_id:
                            job.task_id = new_task_id
                            resumed_count += 1
                            logger.info(f"Resumed job {job.id} ({job.job_type}) with new task {new_task_id}")
                        else:
                            # Mark as failed if we can't create task
                            job.status = JobStatus.FAILED
                            job.error = "Failed to create celery task during resume"
                            logger.error(f"Failed to create celery task for job {job.id}")
                            
                    except Exception as job_error:
                        logger.error(f"Error resuming individual job {job.id}: {job_error}")
                        job.status = JobStatus.FAILED
                        job.error = f"Failed to resume job: {str(job_error)}"
                
                db.commit()
                
                logger.info(f"Resumed {resumed_count} jobs after circuit breaker closed")
                return resumed_count
                
            finally:
                if should_close:
                    db.close()
                    
        except Exception as e:
            logger.error(f"Error resuming jobs on circuit breaker close: {e}")
            if self.db:
                self.db.rollback()
            return 0

    def _create_celery_task_for_job(self, job: Job, max_retries: int = 3) -> Optional[str]:
        """
        Create a new celery task for a resumed job with retry logic.
        
        Returns:
            str: New task ID if successful, None if failed
        """
        for attempt in range(max_retries):
            try:
                # Import celery tasks here to avoid circular imports
                from app.workers.campaign_tasks import process_job_task
                
                # Create celery task based on job type
                if job.job_type == JobType.FETCH_LEADS:
                    result = process_job_task.delay(
                        job_id=job.id,
                        job_type=job.job_type.value,
                        campaign_id=job.campaign_id
                    )
                elif job.job_type == JobType.ENRICH_LEAD:
                    result = process_job_task.delay(
                        job_id=job.id,
                        job_type=job.job_type.value,
                        campaign_id=job.campaign_id
                    )
                elif job.job_type == JobType.CLEANUP_CAMPAIGN:
                    result = process_job_task.delay(
                        job_id=job.id,
                        job_type=job.job_type.value,
                        campaign_id=job.campaign_id
                    )
                else:
                    logger.warning(f"Unknown job type {job.job_type} for job {job.id}")
                    return None
                
                logger.debug(f"Created celery task {result.id} for job {job.id} (attempt {attempt + 1})")
                return result.id
                
            except Exception as e:
                logger.warning(f"Failed to create celery task for job {job.id} (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to create celery task for job {job.id} after {max_retries} attempts")
                    return None
                
        return None

    def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive queue status with simplified circuit breaker info."""
        try:
            if not self.db:
                from app.core.database import SessionLocal
                db = SessionLocal()
                should_close = True
            else:
                db = self.db
                should_close = False
            
            try:
                # Get global circuit breaker status
                circuit_status = self.circuit_breaker.get_circuit_status()
                
                # Get job counts by status
                job_counts = {}
                for status in JobStatus:
                    count = db.query(Job).filter(Job.status == status).count()
                    job_counts[status.value] = count
                
                return {
                    'circuit_breaker': circuit_status,  # Single global circuit breaker
                    'job_counts': job_counts,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            finally:
                if should_close:
                    db.close()
                    
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {'error': str(e)}


def get_queue_manager(redis_client=None) -> QueueManager:
    """Factory function to create QueueManager with dependencies."""
    return QueueManager(redis_client=redis_client, db=None) 