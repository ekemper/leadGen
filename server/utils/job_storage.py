# This module is now deprecated. Job results are persisted in the Postgres Job table.
# All logic for storing and retrieving job results should use the Job model.

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from rq.registry import FinishedJobRegistry, FailedJobRegistry
from rq.job import Job
from server.config.queue_config import get_queue
from server.utils.logging_config import setup_logger, ContextLogger
from server.models.job import Job as JobModel
from server.models.job_status import JobStatus
from server.config.database import db

# Configure module logger
logger = setup_logger('job_storage')

class JobStorage:
    """
    DEPRECATED: Use Job model directly instead.
    Storage for job metadata and results.
    """
    
    def __init__(self):
        """Initialize the job storage."""
        self.logger = logger

    def save_job_result(self, job_id: str, campaign_id: str, result: Dict[str, Any]) -> None:
        """Save a job result."""
        with ContextLogger(self.logger, job_id=job_id, campaign_id=campaign_id):
            try:
                job = JobModel.query.get(job_id)
                if not job:
                    self.logger.warning(f"Job {job_id} not found")
                    return
                
                job.result = result
                job.completed_at = datetime.utcnow()
                job.status = JobStatus.COMPLETED
                db.session.commit()
                
                self.logger.info("Saved job result", extra={
                    'metadata': {
                        'job_id': job_id,
                        'campaign_id': campaign_id
                    }
                })
            except Exception as e:
                self.logger.error(f"Error saving job result: {str(e)}", exc_info=True)
                db.session.rollback()
                raise

    def save_job_error(self, job_id: str, campaign_id: str, error: str) -> None:
        """Save a job error."""
        with ContextLogger(self.logger, job_id=job_id, campaign_id=campaign_id):
            try:
                job = JobModel.query.get(job_id)
                if not job:
                    self.logger.warning(f"Job {job_id} not found")
                    return
                
                job.error_message = error
                job.completed_at = datetime.utcnow()
                job.status = JobStatus.FAILED
                db.session.commit()
                
                self.logger.error("Saved job error", extra={
                    'metadata': {
                        'job_id': job_id,
                        'campaign_id': campaign_id,
                        'error': error
                    }
                })
            except Exception as e:
                self.logger.error(f"Error saving job error: {str(e)}", exc_info=True)
                db.session.rollback()
                raise

    def cleanup_old_jobs(self, campaign_id: str) -> None:
        """Clean up old jobs for a campaign."""
        with ContextLogger(self.logger, campaign_id=campaign_id):
            try:
                # Get all jobs for campaign
                jobs = JobModel.query.filter_by(campaign_id=campaign_id).all()
                
                for job in jobs:
                    if job.status == JobStatus.COMPLETED:
                        db.session.delete(job)
                        self.logger.info(f"Cleaned up old completed job {job.id} for campaign {campaign_id}")
                    elif job.status == JobStatus.FAILED:
                        db.session.delete(job)
                        self.logger.info(f"Cleaned up old failed job {job.id} for campaign {campaign_id}")
                
                db.session.commit()
            except Exception as e:
                self.logger.error(f"Error cleaning up old jobs for campaign {campaign_id}: {str(e)}", exc_info=True)
                db.session.rollback()
                raise

def store_job_result(job: Job, result: Any) -> None:
    """
    Store a job result in the job's result field.
    
    Args:
        job: The RQ job instance
        result: The result to store
    """
    try:
        # Store the result with metadata
        job_result = {
            'id': job.id,
            'type': job.func_name,
            'result': result,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
            'execution_time': (job.ended_at - job.started_at).total_seconds() if job.ended_at and job.started_at else None
        }
        job.result = job_result
        
        logger.info(
            f"Stored result for job {job.id}",
            extra={
                'job_id': job.id,
                'job_type': job.func_name,
                'completed_at': job_result['ended_at']
            }
        )
    except Exception as e:
        logger.error(
            f"Error storing job result: {str(e)}",
            extra={
                'job_id': job.id,
                'error': str(e)
            }
        )

def get_job_results(campaign_id: str) -> Dict[str, List[Dict]]:
    """
    Get all job results for a campaign.
    
    Args:
        campaign_id: The campaign ID to get results for
        
    Returns:
        Dictionary containing completed and failed jobs
    """
    try:
        queue = get_queue()
        registry = FinishedJobRegistry(queue=queue)
        failed_registry = FailedJobRegistry(queue=queue)
        
        results = {
            'completed': [],
            'failed': []
        }
        
        # Get completed jobs
        for job_id in registry.get_job_ids():
            job = queue.fetch_job(job_id)
            if job and job.args and len(job.args) > 0 and job.args[0].get('campaign_id') == campaign_id:
                results['completed'].append({
                    'id': job.id,
                    'type': job.func_name,
                    'result': job.result,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'ended_at': job.ended_at.isoformat() if job.ended_at else None,
                    'execution_time': (job.ended_at - job.started_at).total_seconds() if job.ended_at and job.started_at else None
                })
        
        # Get failed jobs
        for job_id in failed_registry.get_job_ids():
            job = queue.fetch_job(job_id)
            if job and job.args and len(job.args) > 0 and job.args[0].get('campaign_id') == campaign_id:
                results['failed'].append({
                    'id': job.id,
                    'type': job.func_name,
                    'error': str(job.exc_info) if job.exc_info else None,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'ended_at': job.ended_at.isoformat() if job.ended_at else None
                })
        
        return results
    except Exception as e:
        logger.error(
            f"Error getting job results: {str(e)}",
            extra={
                'campaign_id': campaign_id,
                'error': str(e)
            }
        )
        return {'completed': [], 'failed': []}

def cleanup_old_jobs(campaign_id: str, days: int = 7) -> None:
    """
    Clean up jobs older than specified days for a specific campaign.
    
    Args:
        campaign_id: The campaign ID to clean up jobs for
        days: Number of days to keep job results
    """
    try:
        queue = get_queue()
        registry = FinishedJobRegistry(queue=queue)
        failed_registry = FailedJobRegistry(queue=queue)
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Clean up completed jobs
        for job_id in registry.get_job_ids():
            job = queue.fetch_job(job_id)
            if job and job.args and len(job.args) > 0 and job.args[0].get('campaign_id') == campaign_id:
                if job.ended_at and job.ended_at < cutoff:
                    job.delete()
                    logger.info(f"Cleaned up old completed job {job_id} for campaign {campaign_id}")
        
        # Clean up failed jobs
        for job_id in failed_registry.get_job_ids():
            job = queue.fetch_job(job_id)
            if job and job.args and len(job.args) > 0 and job.args[0].get('campaign_id') == campaign_id:
                if job.ended_at and job.ended_at < cutoff:
                    job.delete()
                    logger.info(f"Cleaned up old failed job {job_id} for campaign {campaign_id}")
    except Exception as e:
        logger.error(f"Error cleaning up old jobs for campaign {campaign_id}: {str(e)}") 