"""
Job Status Change Handler

This service handles job status changes and triggers appropriate campaign status updates.
Implements the simplified business rule: ANY paused job → campaign MUST be paused immediately.

REFACTORED: Part of simplified campaign status logic.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.logger import get_logger
from app.models.job import Job, JobStatus
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus

logger = get_logger(__name__)


class JobStatusHandler:
    """
    Handles job status changes and their impact on campaign status.
    
    SIMPLIFIED Business Rules:
    - ANY job paused → campaign MUST be paused immediately
    - Job completion/failure triggers campaign evaluation but NO automatic resume
    - Maintains transactional consistency between job and campaign updates
    """
    
    def __init__(self):
        """Initialize the job status handler."""
        logger.info("JobStatusHandler initialized with simplified logic")
    
    async def handle_job_status_change(self, job: Job, old_status: JobStatus, new_status: JobStatus, db: Session) -> Dict[str, Any]:
        """
        Handle a job status change and evaluate campaign impact.
        
        Args:
            job: Job that changed status
            old_status: Previous job status
            new_status: New job status
            db: Database session
            
        Returns:
            Dict with handling results
        """
        try:
            logger.info(f"Handling job {job.id} status change: {old_status} → {new_status}")
            
            if not job.campaign_id:
                return {
                    "status": "no_action",
                    "reason": "Job has no associated campaign",
                    "job_id": job.id
                }
            
            # Get the campaign
            campaign = db.query(Campaign).filter(Campaign.id == job.campaign_id).first()
            if not campaign:
                logger.warning(f"Campaign {job.campaign_id} not found for job {job.id}")
                return {
                    "status": "error",
                    "reason": "Campaign not found",
                    "job_id": job.id,
                    "campaign_id": job.campaign_id
                }
            
            # SIMPLIFIED RULE 1: ANY job paused → campaign MUST be paused immediately
            if new_status == JobStatus.PAUSED and campaign.status == CampaignStatus.RUNNING:
                return await self._pause_campaign_for_job(campaign, job, db)
            
            # SIMPLIFIED RULE 2: Job failures may trigger campaign pause (like paused jobs)
            elif new_status == JobStatus.FAILED and campaign.status == CampaignStatus.RUNNING:
                return await self._evaluate_campaign_for_job_failure(campaign, job, db)
            
            # SIMPLIFIED RULE 3: Job completion/success does NOT automatically resume campaigns
            elif new_status in [JobStatus.COMPLETED, JobStatus.PROCESSING]:
                # Log the change but no automatic campaign actions
                logger.info(f"Job {job.id} completed/processing - no automatic campaign resume (new logic)")
                return {
                    "status": "no_action",
                    "reason": f"Job {new_status} does not trigger automatic campaign actions",
                    "job_id": job.id,
                    "campaign_id": campaign.id,
                    "new_logic": "manual_resume_only"
                }
            
            # All other status changes: log but no action
            return {
                "status": "no_action",
                "reason": f"Job status {old_status} → {new_status} does not require campaign action",
                "job_id": job.id,
                "campaign_id": campaign.id
            }
            
        except Exception as e:
            logger.error(f"Error handling job {job.id} status change: {str(e)}", exc_info=True)
            db.rollback()
            return {
                "status": "error",
                "reason": str(e),
                "job_id": job.id
            }
    # TODO: Remove this - campaigns will no longer have a paused state
    async def _pause_campaign_for_job(self, campaign: Campaign, job: Job, db: Session) -> Dict[str, Any]:
        """
        Pause campaign immediately due to job pause (simplified rule).
        
        Args:
            campaign: Campaign to pause
            job: Job that was paused
            db: Database session
            
        Returns:
            Dict with pause operation results
        """
        try:
            reason = f"Job {job.name or job.id} paused - auto-pause triggered"
            if job.error:
                reason += f": {job.error}"
            
            # Pause the campaign immediately
            success = campaign.pause(reason)
            
            if success:
                db.commit()
                logger.info(f"Campaign {campaign.id} paused due to job {job.id} pause")
                
                return {
                    "status": "campaign_paused",
                    "campaign_id": campaign.id,
                    "job_id": job.id,
                    "reason": reason,
                    "trigger": "job_paused",
                    "immediate_pause": True
                }
            else:
                logger.error(f"Failed to pause campaign {campaign.id}")
                return {
                    "status": "error",
                    "reason": "Failed to pause campaign",
                    "campaign_id": campaign.id,
                    "job_id": job.id
                }
                
        except Exception as e:
            logger.error(f"Error pausing campaign {campaign.id} for job {job.id}: {str(e)}")
            db.rollback()
            return {
                "status": "error",
                "reason": str(e),
                "campaign_id": campaign.id,
                "job_id": job.id
            }
    
    #TODO : this should only have to be evaluated if the job failure was something other than a third party api failure which will be handled by the circuit breaker logic
    async def _evaluate_campaign_for_job_failure(self, campaign: Campaign, job: Job, db: Session) -> Dict[str, Any]:
        """
        Evaluate campaign status when a job fails.
        
        SIMPLIFIED RULE: Job failures are treated like pauses (immediate campaign pause)
        
        Args:
            campaign: Campaign to evaluate
            job: Job that failed
            db: Database session
            
        Returns:
            Dict with evaluation results
        """
        try:
            # In simplified logic, failures pause campaigns like job pauses
            reason = f"Job {job.name or job.id} failed - auto-pause triggered"
            if job.error:
                reason += f": {job.error}"
            
            success = campaign.pause(reason)
            
            if success:
                db.commit()
                logger.info(f"Campaign {campaign.id} paused due to job {job.id} failure")
                
                return {
                    "status": "campaign_paused",
                    "campaign_id": campaign.id,
                    "job_id": job.id,
                    "reason": reason,
                    "trigger": "job_failed",
                    "immediate_pause": True
                }
            else:
                logger.error(f"Failed to pause campaign {campaign.id}")
                return {
                    "status": "error",
                    "reason": "Failed to pause campaign",
                    "campaign_id": campaign.id,
                    "job_id": job.id
                }
                
        except Exception as e:
            logger.error(f"Error evaluating campaign {campaign.id} for job {job.id} failure: {str(e)}")
            db.rollback()
            return {
                "status": "error",
                "reason": str(e),
                "campaign_id": campaign.id,
                "job_id": job.id
            }
    
    # TODO: Depricated
    async def bulk_evaluate_campaigns_for_service_failure(self, service_name: str, paused_jobs: list, db: Session) -> Dict[str, Any]:
        """
        Evaluate multiple campaigns when a service fails and pauses multiple jobs.
        
        Args:
            service_name: Name of the failed service
            paused_jobs: List of jobs that were paused due to service failure
            db: Database session
            
        Returns:
            Dict with bulk evaluation results
        """
        try:
            logger.info(f"Bulk evaluating campaigns for {service_name} service failure affecting {len(paused_jobs)} jobs")
            
            # Group jobs by campaign
            campaigns_to_pause = {}
            for job in paused_jobs:
                if job.campaign_id:
                    if job.campaign_id not in campaigns_to_pause:
                        campaigns_to_pause[job.campaign_id] = []
                    campaigns_to_pause[job.campaign_id].append(job)
            
            campaigns_paused = 0
            campaign_errors = []
            
            for campaign_id, jobs in campaigns_to_pause.items():
                try:
                    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                    if campaign and campaign.status == CampaignStatus.RUNNING:
                        
                        affected_jobs = len(jobs)
                        reason = f"Service {service_name} unavailable: {affected_jobs} dependent jobs paused"
                        
                        success = campaign.pause(reason)
                        if success:
                            campaigns_paused += 1
                            logger.info(f"Campaign {campaign_id} paused due to {service_name} service failure")
                        else:
                            campaign_errors.append(f"Campaign {campaign_id}: Failed to pause")
                            
                except Exception as e:
                    error_msg = f"Campaign {campaign_id}: {str(e)}"
                    campaign_errors.append(error_msg)
                    logger.error(f"Error evaluating campaign {campaign_id}: {str(e)}")
            
            # Commit all changes
            db.commit()
            
            result = {
                "status": "bulk_evaluation_completed",
                "service": service_name,
                "jobs_affected": len(paused_jobs),
                "campaigns_evaluated": len(campaigns_to_pause),
                "campaigns_paused": campaigns_paused,
                "trigger": "service_failure_bulk"
            }
            
            if campaign_errors:
                result["campaign_errors"] = campaign_errors
            
            logger.info(f"Bulk evaluation for {service_name}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in bulk campaign evaluation for {service_name}: {str(e)}", exc_info=True)
            db.rollback()
            return {
                "status": "error",
                "reason": str(e),
                "service": service_name
            }


def get_job_status_handler() -> JobStatusHandler:
    """Get singleton instance of JobStatusHandler."""
    return JobStatusHandler()


# TODO; this class may be entirely Depricated

# Integration function for easy use
async def handle_job_status_change(job: Job, old_status: JobStatus, new_status: JobStatus, db: Session) -> Dict[str, Any]:
    """
    Convenience function to handle job status changes.
    
    Usage:
        result = await handle_job_status_change(job, JobStatus.PROCESSING, JobStatus.PAUSED, db)
    """
    handler = get_job_status_handler()
    return await handler.handle_job_status_change(job, old_status, new_status, db) 