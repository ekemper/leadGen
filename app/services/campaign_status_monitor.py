"""
Campaign Status Monitoring Service

This service monitors job states and automatically pauses campaigns based on 
job/service failures. ALL RESUME OPERATIONS ARE MANUAL ONLY through queue management.

REFACTORED: Removed all automatic resume logic per simplified business rules.
"""

from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.logger import get_logger
from app.core.circuit_breaker import ThirdPartyService
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus

logger = get_logger(__name__)


class CampaignStatusMonitor:
    """
    Monitors campaign job states and automatically pauses campaigns.
    
    SIMPLIFIED Business Rules (Post-Refactor):
    - Pause campaign immediately when ANY job is paused
    - Pause campaign when circuit breaker opens (via service failure)
    - NO automatic resume logic - campaigns resume ONLY through manual queue management
    - Maintain audit trail of all status changes
    """
    
    def __init__(self):
        """Initialize the campaign status monitor with simplified logic."""
        # No more pause threshold - ANY paused job triggers campaign pause
        logger.info("CampaignStatusMonitor initialized with simplified pause-only logic")
        
    async def evaluate_campaign_status_for_job_change(self, job: Job, db: Session) -> Dict[str, any]:
        """
        Evaluate campaign status when a job status changes.
        
        NEW SIMPLIFIED RULE: ANY paused job → campaign MUST be paused immediately
        
        Args:
            job: Job that changed status
            db: Database session
            
        Returns:
            Dict with evaluation results
        """
        try:
            logger.info(f"Evaluating campaign status for job {job.id} status change to {job.status}")
            
            if not job.campaign_id:
                return {"status": "no_action", "reason": "Job has no associated campaign"}
            
            # Get the campaign
            campaign = db.query(Campaign).filter(Campaign.id == job.campaign_id).first()
            if not campaign:
                logger.warning(f"Campaign {job.campaign_id} not found for job {job.id}")
                return {"status": "error", "reason": "Campaign not found"}
            
            # Check if job is paused and campaign is still running
            if job.status == JobStatus.PAUSED and campaign.status == CampaignStatus.RUNNING:
                # IMMEDIATE PAUSE: ANY paused job pauses the entire campaign
                reason = f"Job {job.name or job.id} paused - auto-pause triggered"
                success = campaign.pause(reason)
                
                if success:
                    db.commit()
                    logger.info(f"Campaign {campaign.id} paused due to job {job.id} pause")
                    return {
                        "status": "paused",
                        "campaign_id": campaign.id,
                        "reason": reason,
                        "trigger_job": job.id
                    }
                else:
                    logger.error(f"Failed to pause campaign {campaign.id}")
                    return {"status": "error", "reason": "Failed to pause campaign"}
            
            # For any other job status changes, no automatic action needed
            return {
                "status": "no_action", 
                "reason": f"Job {job.id} status {job.status} does not require campaign status change"
            }
            
        except Exception as e:
            logger.error(f"Error evaluating campaign status for job {job.id}: {str(e)}", exc_info=True)
            db.rollback()
            return {"status": "error", "reason": str(e)}
    
    async def evaluate_campaign_status_for_service(self, service: ThirdPartyService, db: Session) -> Dict[str, int]:
        """
        Evaluate which campaigns should be paused based on service failure.
        
        SIMPLIFIED RULE: When ANY circuit breaker opens, ALL running campaigns are paused immediately
        No dependency checking, no thresholds - complete system pause on any service failure
        
        Args:
            service: The service that failed
            db: Database session
            
        Returns:
            Dict with keys: campaigns_eligible, campaigns_paused
        """
        try:
            logger.info(f"Circuit breaker opened for {service.value} - pausing ALL running campaigns immediately")
            
            # Get ALL running campaigns - no filtering by dependency
            running_campaigns = (
                db.query(Campaign)
                .filter(Campaign.status == CampaignStatus.RUNNING)
                .all()
            )
            
            campaigns_eligible = len(running_campaigns)
            campaigns_paused = 0
            
            # Pause ALL running campaigns - no evaluation needed
            for campaign in running_campaigns:
                reason = f"System pause: {service.value} circuit breaker opened"
                
                # Pause the campaign immediately
                success = campaign.pause(reason)
                if success:
                    campaigns_paused += 1
                    logger.info(f"Paused campaign {campaign.id} due to {service.value} circuit breaker opening")
                else:
                    logger.warning(f"Failed to pause campaign {campaign.id}")
            
            # Commit all changes
            db.commit()
            
            result = {
                "campaigns_eligible": campaigns_eligible,
                "campaigns_paused": campaigns_paused
            }
            
            logger.info(f"Circuit breaker {service.value} triggered system pause: {campaigns_paused}/{campaigns_eligible} campaigns paused")
            return result
            
        except Exception as e:
            logger.error(f"Error pausing all campaigns for {service.value} circuit breaker: {str(e)}", exc_info=True)
            db.rollback()
            return {"campaigns_eligible": 0, "campaigns_paused": 0}

    # REMOVED METHODS (sophisticated evaluation logic eliminated):
    # - async def evaluate_campaigns_for_service_recovery() → DELETED (automatic resume)
    # - async def evaluate_campaign_resumption() → DELETED (automatic resume)
    # - async def _can_resume_campaign_safely() → DELETED (automatic resume)
    # - async def _can_resume_campaign() → DELETED (automatic resume)
    # - async def _get_required_services_for_campaign() → DELETED (automatic resume)
    # - async def _should_pause_campaign_for_service() → DELETED (dependency checking no longer needed)
    # - async def _get_jobs_dependent_on_service() → DELETED (dependency checking no longer needed)
    
    async def get_campaign_job_statistics(self, campaign: Campaign, db: Session) -> Dict[str, int]:
        """
        Get job statistics for a campaign.
        
        Args:
            campaign: Campaign to analyze
            db: Database session
            
        Returns:
            Dict with job counts by status
        """
        try:
            jobs = db.query(Job).filter(Job.campaign_id == campaign.id).all()
            
            stats = {
                "total_jobs": len(jobs),
                "pending_jobs": len([j for j in jobs if j.status == JobStatus.PENDING]),
                "processing_jobs": len([j for j in jobs if j.status == JobStatus.PROCESSING]),
                "completed_jobs": len([j for j in jobs if j.status == JobStatus.COMPLETED]),
                "failed_jobs": len([j for j in jobs if j.status == JobStatus.FAILED]),
                "paused_jobs": len([j for j in jobs if j.status == JobStatus.PAUSED]),
                "cancelled_jobs": len([j for j in jobs if j.status == JobStatus.CANCELLED])
            }
            
            # Calculate percentages
            if stats["total_jobs"] > 0:
                stats["paused_percentage"] = (stats["paused_jobs"] / stats["total_jobs"]) * 100
            else:
                stats["paused_percentage"] = 0
                
            return stats
            
        except Exception as e:
            logger.error(f"Error getting job statistics for campaign {campaign.id}: {str(e)}")
            return {
                "total_jobs": 0,
                "pending_jobs": 0,
                "processing_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "paused_jobs": 0,
                "cancelled_jobs": 0,
                "paused_percentage": 0
            }

    async def _get_campaigns_paused_by_service(self, service: ThirdPartyService, db: Session) -> List[Campaign]:
        """
        Get campaigns that were paused due to a specific service failure.
        
        Used for reporting and manual resume logic integration.
        """
        try:
            paused_campaigns = (
                db.query(Campaign)
                .filter(Campaign.status == CampaignStatus.PAUSED)
                .all()
            )
            
            # Filter campaigns paused due to this specific service
            service_paused_campaigns = []
            for campaign in paused_campaigns:
                # Check if the status message mentions this service
                if (campaign.status_message and 
                    service.value.lower() in campaign.status_message.lower()):
                    service_paused_campaigns.append(campaign)
            
            return service_paused_campaigns
            
        except Exception as e:
            logger.error(f"Error getting campaigns paused by {service.value}: {str(e)}")
            return []


def get_campaign_status_monitor() -> CampaignStatusMonitor:
    """Get singleton instance of CampaignStatusMonitor."""
    return CampaignStatusMonitor() 