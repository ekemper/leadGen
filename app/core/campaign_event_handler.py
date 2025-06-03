"""
Campaign Event Handler for Circuit Breaker Integration

This module handles automatic campaign pausing and resumption based on 
circuit breaker state changes. It integrates with the existing circuit 
breaker system to provide graceful degradation for campaign execution.
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


class CampaignEventHandler:
    """
    Handles automatic campaign pausing and resumption based on circuit breaker events.
    
    This handler:
    1. Listens for circuit breaker state changes
    2. Automatically pauses running campaigns when services fail
    3. Automatically resumes paused campaigns when services recover
    4. Provides event logging and monitoring
    """
    
    def __init__(self):
        """Initialize the campaign event handler."""
        self.circuit_breaker = get_circuit_breaker()
        
    async def handle_circuit_breaker_opened(self, service: ThirdPartyService, reason: str, metadata: Optional[Dict] = None) -> int:
        """
        Handle circuit breaker opening by pausing all running campaigns.
        
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
            from app.services.campaign import CampaignService
            
            db = SessionLocal()
            campaign_service = CampaignService()
            
            try:
                # Pause all running campaigns dependent on this service
                detailed_reason = self._build_detailed_reason(service, reason, metadata)
                paused_count = await campaign_service.pause_campaigns_for_service(
                    service, detailed_reason, db
                )
                
                logger.info(f"Circuit breaker event: Paused {paused_count} campaigns due to {service.value} failure")
                
                # Log the event for monitoring
                await self._log_campaign_event(
                    event_type="circuit_breaker_opened",
                    service=service,
                    campaigns_affected=paused_count,
                    reason=detailed_reason,
                    metadata=metadata
                )
                
                return paused_count
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error handling circuit breaker opened event for {service.value}: {str(e)}", exc_info=True)
            return 0
    
    async def handle_circuit_breaker_closed(self, service: ThirdPartyService, metadata: Optional[Dict] = None) -> int:
        """
        Handle circuit breaker closing by checking if campaigns can be resumed.
        
        Args:
            service: The service that recovered
            metadata: Additional recovery information
            
        Returns:
            Number of campaigns eligible for resumption
        """
        try:
            logger.info(f"Circuit breaker closed for {service.value} - service recovered")
            
            db = SessionLocal()
            try:
                # Get all paused campaigns that were paused due to this service
                paused_campaigns = await self._get_campaigns_paused_by_service(service, db)
                
                resumable_count = 0
                for campaign in paused_campaigns:
                    # Check if all required services are now available
                    if await self._can_resume_campaign_safely(campaign, db):
                        await self._resume_campaign_if_safe(campaign, db)
                        resumable_count += 1
                
                logger.info(f"Circuit breaker event: {resumable_count} campaigns eligible for resumption after {service.value} recovery")
                
                # Log the event for monitoring
                await self._log_campaign_event(
                    event_type="circuit_breaker_closed",
                    service=service,
                    campaigns_affected=resumable_count,
                    reason=f"{service.value} service recovered",
                    metadata=metadata
                )
                
                return resumable_count
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error handling circuit breaker closed event for {service.value}: {str(e)}", exc_info=True)
            return 0
    
    async def handle_circuit_breaker_half_open(self, service: ThirdPartyService, metadata: Optional[Dict] = None):
        """
        Handle circuit breaker entering half-open state.
        
        In half-open state, we don't automatically resume campaigns yet,
        but we log the event for monitoring.
        """
        try:
            logger.info(f"Circuit breaker half-open for {service.value} - testing recovery")
            
            # Log the event for monitoring
            await self._log_campaign_event(
                event_type="circuit_breaker_half_open",
                service=service,
                campaigns_affected=0,
                reason=f"{service.value} service testing recovery",
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error handling circuit breaker half-open event for {service.value}: {str(e)}", exc_info=True)
    
    async def _get_campaigns_paused_by_service(self, service: ThirdPartyService, db) -> List[Campaign]:
        """Get campaigns that were paused due to a specific service failure."""
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
    
    async def _can_resume_campaign_safely(self, campaign: Campaign, db) -> bool:
        """Check if a campaign can be safely resumed by checking all required services."""
        try:
            # Import here to avoid circular imports
            from app.services.campaign import CampaignService
            
            campaign_service = CampaignService()
            can_start, reason = campaign_service.can_start_campaign(campaign)
            
            # For paused campaigns, we need to check if resume is possible
            # The can_start_campaign checks circuit breaker status
            if campaign.status == CampaignStatus.PAUSED:
                # Check if all required services are available
                required_services = [
                    ThirdPartyService.APOLLO,
                    ThirdPartyService.PERPLEXITY,
                    ThirdPartyService.OPENAI,
                    ThirdPartyService.INSTANTLY,
                    ThirdPartyService.MILLIONVERIFIER
                ]
                
                for service in required_services:
                    allowed, service_reason = self.circuit_breaker.should_allow_request(service)
                    if not allowed:
                        return False
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if campaign {campaign.id} can be resumed: {str(e)}")
            return False
    
    async def _resume_campaign_if_safe(self, campaign: Campaign, db):
        """Resume a campaign if it's safe to do so."""
        try:
            # Import here to avoid circular imports
            from app.services.campaign import CampaignService
            
            campaign_service = CampaignService()
            
            # Resume the campaign
            result = await campaign_service.resume_campaign(campaign.id, db)
            logger.info(f"Auto-resumed campaign {campaign.id}: {result.get('message', 'resumed')}")
            
        except Exception as e:
            logger.error(f"Error auto-resuming campaign {campaign.id}: {str(e)}")
    
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
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'service': service.value,
                'campaigns_affected': campaigns_affected,
                'reason': reason,
                'metadata': metadata or {}
            }
            
            # Log at appropriate level based on event type
            if event_type == "circuit_breaker_opened":
                logger.warning(f"Campaign Event: {event_type} - {campaigns_affected} campaigns affected by {service.value} failure")
            else:
                logger.info(f"Campaign Event: {event_type} - {campaigns_affected} campaigns affected by {service.value} recovery")
            
            # You could also store this in Redis or a database for analytics
            # For now, we just log it
            
        except Exception as e:
            logger.error(f"Error logging campaign event: {str(e)}")


# Global event handler instance
_campaign_event_handler = None

def get_campaign_event_handler() -> CampaignEventHandler:
    """Get the global campaign event handler instance."""
    global _campaign_event_handler
    if _campaign_event_handler is None:
        _campaign_event_handler = CampaignEventHandler()
    return _campaign_event_handler 