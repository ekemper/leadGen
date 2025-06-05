"""
Job Resume Service

This service handles the reliable resumption of paused jobs when the circuit breaker closes.
Provides comprehensive error handling, retry logic, and detailed status reporting.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.logger import get_logger
from app.models.job import Job, JobStatus, JobType
from app.models.campaign import Campaign

logger = get_logger(__name__)


class JobResumeService:
    """
    Service for handling bulk job resume operations with reliable celery task creation.
    
    Features:
    - Bulk job resume with atomic database operations
    - Retry logic for failed task creation
    - Comprehensive error handling and reporting
    - Detailed resume status tracking
    """
    
    def __init__(self, db: Session):
        """Initialize the job resume service with database session."""
        self.db = db

    def resume_all_paused_jobs(self, reason: str = "Circuit breaker closed") -> Dict[str, Any]:
        """
        Resume all paused jobs and create new celery tasks.
        
        Args:
            reason: Reason for resuming jobs
            
        Returns:
            Dict containing resume operation results
        """
        try:
            logger.info(f"Starting bulk job resume operation: {reason}")
            
            # Get all paused jobs
            paused_jobs = (
                self.db.query(Job)
                .filter(Job.status == JobStatus.PAUSED)
                .all()
            )
            
            if not paused_jobs:
                logger.info("No paused jobs found to resume")
                return {
                    "success": True,
                    "total_jobs": 0,
                    "jobs_resumed": 0,
                    "jobs_failed": 0,
                    "errors": [],
                    "message": "No paused jobs found to resume"
                }
            
            logger.info(f"Found {len(paused_jobs)} paused jobs to resume")
            
            # Process jobs in batches for better performance
            batch_size = 50
            total_resumed = 0
            total_failed = 0
            errors = []
            
            for i in range(0, len(paused_jobs), batch_size):
                batch = paused_jobs[i:i + batch_size]
                batch_result = self._resume_job_batch(batch, reason)
                
                total_resumed += batch_result["resumed"]
                total_failed += batch_result["failed"]
                errors.extend(batch_result["errors"])
            
            # Commit all changes
            self.db.commit()
            
            result = {
                "success": True,
                "total_jobs": len(paused_jobs),
                "jobs_resumed": total_resumed,
                "jobs_failed": total_failed,
                "errors": errors,
                "message": f"Resume operation completed: {total_resumed} resumed, {total_failed} failed"
            }
            
            logger.info(f"Bulk job resume completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in bulk job resume operation: {str(e)}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "total_jobs": 0,
                "jobs_resumed": 0,
                "jobs_failed": 0,
                "errors": [f"Bulk operation failed: {str(e)}"],
                "message": f"Resume operation failed: {str(e)}"
            }

    def _resume_job_batch(self, jobs: List[Job], reason: str) -> Dict[str, Any]:
        """
        Resume a batch of jobs with error handling.
        
        Args:
            jobs: List of jobs to resume
            reason: Reason for resuming
            
        Returns:
            Dict with batch processing results
        """
        resumed_count = 0
        failed_count = 0
        errors = []
        
        for job in jobs:
            try:
                result = self._resume_single_job(job, reason)
                if result["success"]:
                    resumed_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Job {job.id}: {result['error']}")
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Job {job.id}: Unexpected error - {str(e)}"
                errors.append(error_msg)
                logger.error(f"Unexpected error resuming job {job.id}: {str(e)}", exc_info=True)
        
        return {
            "resumed": resumed_count,
            "failed": failed_count,
            "errors": errors
        }

    def _resume_single_job(self, job: Job, reason: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Resume a single job with retry logic for task creation.
        
        Args:
            job: Job to resume
            reason: Reason for resuming
            max_retries: Maximum retries for task creation
            
        Returns:
            Dict with operation result
        """
        try:
            # Update job status first
            original_error = job.error
            job.status = JobStatus.PENDING
            job.error = None
            job.updated_at = datetime.utcnow()
            
            # Try to create celery task with retries
            task_id = None
            for attempt in range(max_retries):
                try:
                    task_id = self._create_celery_task(job)
                    if task_id:
                        break
                except Exception as e:
                    logger.warning(f"Task creation attempt {attempt + 1} failed for job {job.id}: {str(e)}")
                    if attempt == max_retries - 1:
                        # Final attempt failed
                        job.status = JobStatus.FAILED
                        job.error = f"Failed to create celery task after {max_retries} attempts: {str(e)}"
                        return {
                            "success": False,
                            "error": job.error
                        }
            
            # Update job with new task ID
            if task_id:
                job.task_id = task_id
                logger.info(f"Successfully resumed job {job.id} with task {task_id}")
                return {
                    "success": True,
                    "task_id": task_id,
                    "previous_error": original_error
                }
            else:
                job.status = JobStatus.FAILED
                job.error = f"Failed to create celery task - no task ID returned"
                return {
                    "success": False,
                    "error": job.error
                }
                
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = f"Failed to resume job: {str(e)}"
            return {
                "success": False,
                "error": job.error
            }

    def _create_celery_task(self, job: Job) -> Optional[str]:
        """
        Create celery task for a specific job type.
        
        Args:
            job: Job to create task for
            
        Returns:
            Task ID if successful, None if failed
        """
        try:
            # Import here to avoid circular imports
            from app.workers.campaign_tasks import process_job_task
            
            # Create task based on job type
            if job.job_type == JobType.FETCH_LEADS:
                # Get campaign info for fetch leads task
                campaign = self.db.query(Campaign).filter(Campaign.id == job.campaign_id).first()
                if not campaign:
                    raise Exception(f"Campaign {job.campaign_id} not found for FETCH_LEADS job")
                
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
                raise Exception(f"Unknown job type: {job.job_type}")
            
            return result.id
            
        except Exception as e:
            logger.error(f"Error creating celery task for job {job.id}: {str(e)}")
            raise

    def get_resume_status(self) -> Dict[str, Any]:
        """
        Get current status of jobs that can be resumed.
        
        Returns:
            Dict with resume status information
        """
        try:
            paused_jobs = (
                self.db.query(Job)
                .filter(Job.status == JobStatus.PAUSED)
                .all()
            )
            
            # Group by job type
            job_counts = {}
            for job in paused_jobs:
                job_type = job.job_type.value
                if job_type not in job_counts:
                    job_counts[job_type] = 0
                job_counts[job_type] += 1
            
            # Check circuit breaker status
            from app.core.circuit_breaker import get_circuit_breaker
            circuit_breaker = get_circuit_breaker()
            can_resume = circuit_breaker.should_allow_request()
            
            return {
                "total_paused_jobs": len(paused_jobs),
                "paused_by_type": job_counts,
                "can_resume": can_resume,
                "circuit_breaker_state": "closed" if can_resume else "open",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting resume status: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


def get_job_resume_service(db: Session) -> JobResumeService:
    """Factory function to create JobResumeService."""
    return JobResumeService(db) 