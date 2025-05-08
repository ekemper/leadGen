from datetime import datetime
from typing import Dict, Any, List, Optional
from server.models import Job
from server.config.database import db
from server.utils.logging_config import server_logger
from server.models.job_status import JobStatus
from server.api.schemas import JobSchema

class JobService:
    def __init__(self):
        self._ensure_transaction()

    def _ensure_transaction(self):
        """Ensure we have an active transaction."""
        if not db.session.is_active:
            db.session.begin()

    def get_jobs(self, campaign_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all jobs, optionally filtered by campaign_id."""
        try:
            server_logger.info('Fetching jobs')
            self._ensure_transaction()
            
            query = Job.query
            if campaign_id:
                query = query.filter_by(campaign_id=campaign_id)
            jobs = query.order_by(Job.created_at.desc()).all()
            
            job_list = []
            for job in jobs:
                try:
                    job_dict = job.to_dict()
                    # Validate job data
                    errors = JobSchema().validate(job_dict)
                    if errors:
                        raise ValueError(f"Invalid job data: {errors}")
                    job_list.append(job_dict)
                except Exception as e:
                    server_logger.error(f'Error converting job {job.id} to dict: {str(e)}', exc_info=True)
                    continue
            
            return job_list
        except Exception as e:
            server_logger.error(f'Error getting jobs: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get a single job by ID."""
        try:
            server_logger.info(f'Fetching job {job_id}')
            self._ensure_transaction()
            
            job = Job.query.get(job_id)
            if not job:
                server_logger.warning(f'Job {job_id} not found')
                return None
            
            job_dict = job.to_dict()
            # Validate job data
            errors = JobSchema().validate(job_dict)
            if errors:
                raise ValueError(f"Invalid job data: {errors}")
            
            return job_dict
        except Exception as e:
            server_logger.error(f'Error getting job: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def create_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job."""
        try:
            # Validate input data
            errors = JobSchema().validate(data)
            if errors:
                raise ValueError(f"Invalid job data: {errors}")
                
            job = Job(
                campaign_id=data['campaign_id'],
                job_type=data['job_type'],
                status=JobStatus.PENDING,
                parameters=data.get('parameters', {})
            )
            
            db.session.add(job)
            db.session.commit()
            
            job_dict = job.to_dict()
            # Validate output data
            errors = JobSchema().validate(job_dict)
            if errors:
                raise ValueError(f"Invalid job data: {errors}")
                
            return job_dict
        except Exception as e:
            server_logger.error(f'Error creating job: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def update_job_status(self, job_id: str, status: JobStatus, error_message: Optional[str] = None) -> Dict[str, Any]:
        """Update a job's status."""
        try:
            server_logger.info(f'Updating job {job_id} status to {status}')
            self._ensure_transaction()
            
            job = Job.query.get(job_id)
            if not job:
                server_logger.warning(f'Job {job_id} not found')
                return None
            
            job.status = status
            if error_message:
                job.error_message = error_message
            
            db.session.commit()
            
            job_dict = job.to_dict()
            # Validate job data
            errors = JobSchema().validate(job_dict)
            if errors:
                raise ValueError(f"Invalid job data: {errors}")
            
            return job_dict
        except Exception as e:
            server_logger.error(f'Error updating job status: {str(e)}', exc_info=True)
            db.session.rollback()
            raise 