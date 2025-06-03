from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import Depends

from app.core.logger import get_logger
from app.core.circuit_breaker import CircuitBreakerService, ThirdPartyService
from app.models.job import Job, JobStatus, JobType
from app.models.lead import Lead
from app.core.config import get_redis_connection
from app.core.database import get_db

logger = get_logger(__name__)

class QueueManager:
    """
    Manages job queues and integrates with circuit breaker for automatic pausing.
    
    Features:
    - Checks circuit breaker before processing jobs
    - Pauses jobs when services are unavailable
    - Resumes jobs when services recover
    - Maintains job state and traceability
    """
    
    def __init__(self, db: Session, circuit_breaker: CircuitBreakerService):
        self.db = db
        self.circuit_breaker = circuit_breaker
    
    def should_process_job(self, job: Job) -> tuple[bool, str]:
        """
        Check if a job should be processed based on circuit breaker status.
        
        Returns:
            tuple: (should_process, reason)
        """
        if job.job_type == JobType.FETCH_LEADS:
            # Apollo service
            allowed, reason = self.circuit_breaker.should_allow_request(ThirdPartyService.APOLLO)
            return allowed, reason
            
        elif job.job_type == JobType.ENRICH_LEAD:
            # Check all services needed for enrichment
            services_needed = [
                ThirdPartyService.MILLIONVERIFIER,  # Email verification
                ThirdPartyService.PERPLEXITY,       # Lead enrichment
                ThirdPartyService.OPENAI,           # Email copy generation
                ThirdPartyService.INSTANTLY         # Lead creation
            ]
            
            # If any critical service is down, don't process
            for service in services_needed:
                allowed, reason = self.circuit_breaker.should_allow_request(service)
                if not allowed:
                    return False, f"Required service {service.value} unavailable: {reason}"
            
            return True, "All required services available"
            
        else:
            # Unknown job type, allow processing
            return True, "Unknown job type - allowing"
    
    def pause_jobs_for_service(self, service: ThirdPartyService, reason: str = "circuit_breaker") -> int:
        """
        Pause all pending jobs that depend on a specific service.
        
        Returns:
            int: Number of jobs paused
        """
        try:
            # Define which job types depend on which services
            service_job_mapping = {
                ThirdPartyService.APOLLO: [JobType.FETCH_LEADS],
                ThirdPartyService.PERPLEXITY: [JobType.ENRICH_LEAD],
                ThirdPartyService.OPENAI: [JobType.ENRICH_LEAD],
                ThirdPartyService.MILLIONVERIFIER: [JobType.ENRICH_LEAD],
                ThirdPartyService.INSTANTLY: [JobType.ENRICH_LEAD]
            }
            
            affected_job_types = service_job_mapping.get(service, [])
            if not affected_job_types:
                return 0
            
            # Find pending jobs of affected types
            pending_jobs = (
                self.db.query(Job)
                .filter(
                    Job.status == JobStatus.PENDING,
                    Job.job_type.in_(affected_job_types)
                )
                .all()
            )
            
            paused_count = 0
            for job in pending_jobs:
                job.status = JobStatus.PAUSED
                job.error = f"Paused due to {service.value} service unavailability: {reason}"
                job.updated_at = datetime.utcnow()
                paused_count += 1
                
                logger.info(f"Paused job {job.id} ({job.job_type}) due to {service.value} circuit breaker")
            
            self.db.commit()
            
            logger.warning(f"Paused {paused_count} jobs due to {service.value} service failure")
            return paused_count
            
        except Exception as e:
            logger.error(f"Error pausing jobs for service {service}: {e}")
            self.db.rollback()
            return 0
    
    def resume_jobs_for_service(self, service: ThirdPartyService) -> int:
        """
        Resume paused jobs when a service becomes available.
        
        Returns:
            int: Number of jobs resumed
        """
        try:
            # Find paused jobs that were paused due to this service
            paused_jobs = (
                self.db.query(Job)
                .filter(
                    Job.status == JobStatus.PAUSED,
                    Job.error.like(f"%{service.value}%")
                )
                .all()
            )
            
            resumed_count = 0
            for job in paused_jobs:
                job.status = JobStatus.PENDING
                job.error = None  # Clear the pause error
                job.updated_at = datetime.utcnow()
                resumed_count += 1
                
                logger.info(f"Resumed job {job.id} ({job.job_type}) - {service.value} service recovered")
            
            self.db.commit()
            
            logger.info(f"Resumed {resumed_count} jobs - {service.value} service recovered")
            return resumed_count
            
        except Exception as e:
            logger.error(f"Error resuming jobs for service {service}: {e}")
            self.db.rollback()
            return 0
    
    def get_paused_jobs_by_service(self, service: ThirdPartyService) -> List[Job]:
        """Get all jobs paused due to a specific service."""
        try:
            return (
                self.db.query(Job)
                .filter(
                    Job.status == JobStatus.PAUSED,
                    Job.error.like(f"%{service.value}%")
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting paused jobs for service {service}: {e}")
            return []
    
    def get_paused_leads_for_recovery(self, service: ThirdPartyService) -> List[Dict[str, Any]]:
        """
        Get lead information for paused enrichment jobs that need to be recovered.
        
        Returns:
            List of dicts with lead_id, campaign_id, and job_id for recovery
        """
        try:
            paused_jobs = self.get_paused_jobs_by_service(service)
            
            recovery_info = []
            for job in paused_jobs:
                if job.job_type == JobType.ENRICH_LEAD:
                    # Get the lead associated with this job
                    lead = (
                        self.db.query(Lead)
                        .filter(Lead.enrichment_job_id == job.id)
                        .first()
                    )
                    
                    if lead:
                        recovery_info.append({
                            'lead_id': lead.id,
                            'campaign_id': job.campaign_id,
                            'job_id': job.id,
                            'lead_email': lead.email,
                            'paused_at': job.updated_at.isoformat() if job.updated_at else None
                        })
                    else:
                        # If no lead found, just include basic job info
                        recovery_info.append({
                            'lead_id': None,
                            'campaign_id': job.campaign_id,
                            'job_id': job.id,
                            'lead_email': None,
                            'paused_at': job.updated_at.isoformat() if job.updated_at else None
                        })
            
            return recovery_info
            
        except Exception as e:
            logger.error(f"Error getting paused leads for service {service}: {e}")
            return []
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive queue status including circuit breaker info."""
        try:
            # Get circuit breaker status
            circuit_status = self.circuit_breaker.get_circuit_status()
            
            # Get job counts by status
            job_counts = {}
            for status in JobStatus:
                count = self.db.query(Job).filter(Job.status == status).count()
                job_counts[status.value] = count
            
            # Get paused jobs by service
            paused_by_service = {}
            for service in ThirdPartyService:
                paused_jobs = self.get_paused_jobs_by_service(service)
                paused_by_service[service.value] = len(paused_jobs)
            
            return {
                'circuit_breakers': circuit_status,
                'job_counts': job_counts,
                'paused_jobs_by_service': paused_by_service,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {'error': str(e)}


def get_queue_manager(db: Session = Depends(get_db)) -> QueueManager:
    """Factory function to create QueueManager with dependencies."""
    redis_client = get_redis_connection()
    circuit_breaker = CircuitBreakerService(redis_client)
    return QueueManager(db, circuit_breaker) 