"""
Campaign Event Handler for Circuit Breaker Integration

This module handles automatic campaign pausing based on circuit breaker state changes.
ALL RESUME OPERATIONS ARE MANUAL ONLY through queue management.

REFACTORED: Removed all automatic resume logic per simplified business rules.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from app.core.logger import get_logger
from app.core.circuit_breaker import ThirdPartyService, CircuitState, get_circuit_breaker
from app.core.database import SessionLocal
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus

logger = get_logger(__name__)

# TODO: COMPLETELY REMOVE THIS DEPRICATED CLASS. all pauseing will be at the job level
class CampaignEventHandler:
    """
    Handles automatic campaign pausing based on circuit breaker events.
    
    SIMPLIFIED Handler (Post-Refactor):
    1. Listens for circuit breaker state changes
    2. Automatically pauses running campaigns when services fail
    3. NO automatic resume logic - campaigns resume ONLY through manual queue management
    4. Provides event logging and monitoring
    """
    
    def __init__(self):
        """Initialize the campaign event handler with pause-only logic."""
        self.circuit_breaker = get_circuit_breaker()
        logger.info("CampaignEventHandler initialized with simplified pause-only logic")
        
    async def handle_circuit_breaker_opened(self, service: ThirdPartyService, reason: str, metadata: Optional[Dict] = None) -> int:
        """
        Handle circuit breaker opening by evaluating which campaigns should be paused.
        
        Uses the CampaignStatusMonitor to pause dependent campaigns immediately.
        
        Args:
            service: The service that failed
            reason: Reason for the failure
            metadata: Additional failure information
            
        Returns:
            Number of campaigns paused
        """
        try:
            logger.warning(f"Circuit breaker opened for {service.value}: {reason}")
            
            # Import here to avoid circular imports
            from app.services.campaign_status_monitor import get_campaign_status_monitor
            
            db = SessionLocal()
            campaign_monitor = get_campaign_status_monitor()
            
            try:
                # Use the monitoring service to evaluate and pause campaigns
                result = await campaign_monitor.evaluate_campaign_status_for_service(service, db)
                
                paused_count = result["campaigns_paused"]
                eligible_count = result["campaigns_eligible"]
                
                logger.info(f"Circuit breaker event: Evaluated {eligible_count} campaigns, paused {paused_count} due to {service.value} failure")
                
                # Build detailed reason for logging
                detailed_reason = self._build_detailed_reason(service, reason, metadata)
                
                # Log the event for monitoring
                await self._log_campaign_event(
                    event_type="circuit_breaker_opened",
                    service=service,
                    campaigns_affected=paused_count,
                    reason=detailed_reason,
                    metadata={
                        **(metadata or {}),
                        "campaigns_evaluated": eligible_count,
                        "campaigns_paused": paused_count,
                        "immediate_pause": "simplified logic applied"
                    }
                )
                
                return paused_count
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error handling circuit breaker opened event for {service.value}: {str(e)}", exc_info=True)
            return 0
    

    #TODO: refactor how we handle the manual resume of the queue. the state of the campaign should only be created, running, or completed
    #TODO: nothing should have to happen to the campaign when the breaker is manually closed , no state change will be needed. It will be the jobs that will be updated to a pending state and resumed with new celery task instantiation
    async def handle_circuit_breaker_closed(self, service: ThirdPartyService, metadata: Optional[Dict] = None) -> int:
        """
        Handle circuit breaker closing (LOG ONLY - no automatic resume).
        
        Circuit breaker closing does NOT automatically resume campaigns.
        Campaigns require manual resume through queue management API.
        
        Args:
            service: The service that recovered
            metadata: Additional recovery information
            
        Returns:
            Always 0 (no campaigns automatically resumed)
        """
        try:
            logger.info(f"Circuit breaker closed for {service.value} - NO automatic campaign resume (new logic)")
            
            # Log the event for monitoring (no automatic actions)
            await self._log_campaign_event(
                event_type="circuit_breaker_closed",
                service=service,
                campaigns_affected=0,
                reason=f"{service.value} service recovered - manual resume required",
                metadata={
                    **(metadata or {}),
                    "automatic_resume": "disabled",
                    "manual_resume_required": True,
                    "resume_method": "queue_management_api"
                }
            )
            
            # Return 0 - no campaigns automatically resumed
            return 0
                
        except Exception as e:
            logger.error(f"Error handling circuit breaker closed event for {service.value}: {str(e)}", exc_info=True)
            return 0
    #TODO: completely remove the concept of a half open breaker
    async def handle_circuit_breaker_half_open(self, service: ThirdPartyService, metadata: Optional[Dict] = None):
        """
        Handle circuit breaker entering half-open state (LOG ONLY).
        
        In half-open state, we only log the event for monitoring.
        No automatic campaign actions are taken.
        """
        try:
            logger.info(f"Circuit breaker half-open for {service.value} - testing recovery (log only)")
            
            # Log the event for monitoring
            await self._log_campaign_event(
                event_type="circuit_breaker_half_open",
                service=service,
                campaigns_affected=0,
                reason=f"{service.value} service testing recovery",
                metadata={
                    **(metadata or {}),
                    "automatic_actions": "none",
                    "status": "monitoring_only"
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling circuit breaker half-open event for {service.value}: {str(e)}", exc_info=True)
    
    # TODO this will likely be deprecated because we wont need to pause campaigns
    async def _get_campaigns_paused_by_service(self, service: ThirdPartyService, db) -> List[Campaign]:
        """
        Get campaigns that were paused due to a specific service failure.
        
        NOTE: This method retained for potential manual resume logic integration.
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
    
    # TODO: we will want to know why the queue has been stopped but we wont keep the paused state on the campaigns anymore
    # TODO the reason for the breaker triggering will be stored on the breaker class
    def _build_detailed_reason(self, service: ThirdPartyService, reason: str, metadata: Optional[Dict] = None) -> str:
        """Build a detailed reason string for campaign pausing."""
        base_reason = f"Circuit breaker opened for {service.value}: {reason}"
        
        if metadata:
            failure_count = metadata.get('failure_count')
            error_type = metadata.get('error_type')
            
            if failure_count:
                base_reason += f" (failures: {failure_count})"
            if error_type:
                base_reason += f" (type: {error_type})"
        
        return base_reason
    
    async def _log_campaign_event(self, event_type: str, service: ThirdPartyService, 
                                 campaigns_affected: int, reason: str, 
                                 metadata: Optional[Dict] = None):
        """Log campaign events for monitoring and analytics."""
        try:
            event_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "service": service.value,
                "campaigns_affected": campaigns_affected,
                "reason": reason,
                "metadata": metadata or {}
            }
            
            # Log for monitoring systems
            logger.info(f"Campaign event logged: {event_data}")
            
            # Future: Send to monitoring/analytics system
            # await monitoring_service.log_campaign_event(event_data)
            
        except Exception as e:
            logger.error(f"Error logging campaign event: {str(e)}")


def get_campaign_event_handler() -> CampaignEventHandler:
    """Get singleton instance of CampaignEventHandler."""
    return CampaignEventHandler() 