from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.queue_manager import get_queue_manager, QueueManager
from app.core.circuit_breaker import ThirdPartyService, CircuitBreakerService
from app.core.config import get_redis_connection
from app.core.logger import get_logger
from app.models.campaign_status import CampaignStatus

logger = get_logger(__name__)

router = APIRouter()

class ServicePauseRequest(BaseModel):
    service: str
    reason: str = "manual_pause"

class ServiceResumeRequest(BaseModel):
    service: str

class BulkCampaignPauseRequest(BaseModel):
    service: str
    reason: str = "manual_bulk_pause"

class BulkCampaignResumeRequest(BaseModel):
    service: str

class QueueStatusResponse(BaseModel):
    status: str
    data: Dict[str, Any]


# TODO: these campaign related schemas will have to be consolidated. 
# Campaign-specific schemas for queue management responses
class CampaignSummaryItem(BaseModel):
    """Schema for individual campaign in status summaries."""
    id: str = Field(..., description="Campaign ID")
    name: str = Field(..., description="Campaign name")
    status: str = Field(..., description="Campaign status (uppercase enum value)")
    status_message: Optional[str] = Field(None, description="Campaign status message")
    created_at: Optional[str] = Field(None, description="Campaign creation timestamp")
    updated_at: Optional[str] = Field(None, description="Campaign last update timestamp")

class CampaignStatusTotals(BaseModel):
    """Schema for campaign status totals."""
    total_campaigns: int = Field(..., description="Total number of campaigns")
    RUNNING: int = Field(..., description="Number of running campaigns")
    PAUSED: int = Field(..., description="Number of paused campaigns")
    CREATED: int = Field(..., description="Number of created campaigns")
    COMPLETED: int = Field(..., description="Number of completed campaigns")
    FAILED: int = Field(..., description="Number of failed campaigns")

class CampaignStatusSummary(BaseModel):
    """Schema for campaigns organized by status."""
    RUNNING: List[CampaignSummaryItem] = Field(..., description="Running campaigns")
    PAUSED: List[CampaignSummaryItem] = Field(..., description="Paused campaigns")
    CREATED: List[CampaignSummaryItem] = Field(..., description="Created campaigns")
    COMPLETED: List[CampaignSummaryItem] = Field(..., description="Completed campaigns")
    FAILED: List[CampaignSummaryItem] = Field(..., description="Failed campaigns")

class CampaignStatusData(BaseModel):
    """Schema for campaign status endpoint response data."""
    totals: CampaignStatusTotals = Field(..., description="Campaign counts by status")
    campaigns_by_status: CampaignStatusSummary = Field(..., description="Campaigns organized by status")
    paused_by_service: Dict[str, List[CampaignSummaryItem]] = Field(..., description="Paused campaigns organized by service")
    timestamp: Optional[str] = Field(None, description="Response timestamp")

class CampaignStatusResponse(BaseModel):
    """Schema for campaign status endpoint response."""
    status: str = Field(..., description="Response status")
    data: CampaignStatusData = Field(..., description="Campaign status data")

class PausedCampaignsData(BaseModel):
    """Schema for paused campaigns by service response data."""
    service: str = Field(..., description="Service name")
    paused_campaigns: List[CampaignSummaryItem] = Field(..., description="Campaigns paused due to this service")
    count: int = Field(..., description="Number of paused campaigns")
    message: str = Field(..., description="Response message")

class PausedCampaignsResponse(BaseModel):
    """Schema for paused campaigns by service endpoint response."""
    status: str = Field(..., description="Response status")
    data: PausedCampaignsData = Field(..., description="Paused campaigns data")

@router.get("/status", response_model=QueueStatusResponse)
async def get_queue_status(
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get comprehensive queue and circuit breaker status."""
    try:
        status_data = queue_manager.get_queue_status()
        
        return QueueStatusResponse(
            status="success",
            data=status_data
        )
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting queue status: {str(e)}"
        )

@router.post("/pause-service", response_model=QueueStatusResponse)
async def pause_service(
    request: ServicePauseRequest,
    queue_manager: QueueManager = Depends(get_queue_manager),
    db: Session = Depends(get_db)
):
    """Manually pause a service and its related queues and campaigns."""
    try:
        # Validate service name
        try:
            service = ThirdPartyService(request.service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {request.service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        # Manually open the circuit breaker (this pauses all services globally)
        queue_manager.circuit_breaker.record_failure(f"Manual pause requested for {service.value}", request.reason)
        
        # Pause related jobs for all services (since circuit breaker is now global)
        paused_jobs = queue_manager.pause_all_jobs_on_breaker_open(request.reason)
        
        # Pause related campaigns
        from app.services.campaign import CampaignService
        campaign_service = CampaignService()
        paused_campaigns = await campaign_service.pause_campaigns_for_service(service, request.reason, db)
        
        return QueueStatusResponse(
            status="success",
            data={
                "service": service.value,
                "paused": True,
                "reason": request.reason,
                "jobs_paused": paused_jobs,
                "campaigns_paused": paused_campaigns,
                "circuit_breaker_state": "open",
                "message": f"Circuit breaker opened due to {service.value} issues: {paused_jobs} jobs and {paused_campaigns} campaigns paused"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing service {request.service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error pausing service: {str(e)}"
        )

@router.post("/resume-service", response_model=QueueStatusResponse)
async def resume_service(
    request: ServiceResumeRequest,
    queue_manager: QueueManager = Depends(get_queue_manager),
    db: Session = Depends(get_db)
):
    """
    NOTE: In the simplified circuit breaker model, service-specific resume is not supported.
    This endpoint now redirects to global queue resume logic.
    """
    try:
        # Validate service name
        try:
            service = ThirdPartyService(request.service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {request.service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        logger.info(f"Service-specific resume requested for {service.value} - redirecting to global queue resume")
        
        # Check if circuit breaker is already closed
        current_state = queue_manager.circuit_breaker.get_global_circuit_state()
        
        if current_state.value == "closed":
            return QueueStatusResponse(
                status="success",
                data={
                    "service": service.value,
                    "resumed": False,
                    "jobs_resumed": 0,
                    "campaigns_resumed": 0,
                    "circuit_breaker_state": "closed",
                    "message": f"Circuit breaker is already closed. Use /resume-queue endpoint to resume all paused campaigns and jobs."
                }
            )
        
        # Circuit breaker is open - cannot resume individual services
        return QueueStatusResponse(
            status="error",
            data={
                "service": service.value,
                "resumed": False,
                "circuit_breaker_state": current_state.value,
                "message": f"Cannot resume individual services. Circuit breaker is {current_state.value}. Please use /resume-queue endpoint after addressing all service issues."
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming service {request.service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming service: {str(e)}"
        )

@router.get("/paused-jobs/{service}", response_model=QueueStatusResponse)
async def get_paused_jobs_for_service(
    service: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get paused jobs for a specific service."""
    try:
        # Validate service name
        try:
            service_enum = ThirdPartyService(service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        paused_jobs = queue_manager.get_paused_jobs_by_service(service_enum)
        
        # Convert jobs to dict format
        jobs_data = []
        for job in paused_jobs:
            jobs_data.append({
                "id": job.id,
                "name": job.name,
                "job_type": job.job_type.value,
                "campaign_id": job.campaign_id,
                "error": job.error,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None
            })
        
        return QueueStatusResponse(
            status="success",
            data={
                "service": service_enum.value,
                "paused_jobs": jobs_data,
                "count": len(jobs_data)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paused jobs for service {service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting paused jobs: {str(e)}"
        )

@router.get("/paused-leads/{service}", response_model=QueueStatusResponse)
async def get_paused_leads_for_service(
    service: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get lead recovery information for paused enrichment jobs."""
    try:
        # Validate service name
        try:
            service_enum = ThirdPartyService(service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        recovery_info = queue_manager.get_paused_leads_for_recovery(service_enum)
        
        return QueueStatusResponse(
            status="success",
            data={
                "service": service_enum.value,
                "paused_leads": recovery_info,
                "count": len(recovery_info),
                "message": f"Found {len(recovery_info)} leads that need recovery for {service_enum.value}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paused leads for service {service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting paused leads: {str(e)}"
        )

@router.get("/circuit-breakers", response_model=QueueStatusResponse)
async def get_circuit_breaker_status():
    """Get status of the global circuit breaker."""
    try:
        redis_client = get_redis_connection()
        circuit_breaker = CircuitBreakerService(redis_client)
        
        status_data = circuit_breaker.get_circuit_status()
        
        return QueueStatusResponse(
            status="success",
            data={
                "circuit_breaker": status_data,  # Changed from circuit_breakers to circuit_breaker (global)
                "timestamp": status_data.get("timestamp", "unknown")
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting circuit breaker status: {str(e)}"
        )

@router.post("/pause-campaigns-for-service", response_model=QueueStatusResponse)
async def pause_campaigns_for_service(
    request: BulkCampaignPauseRequest,
    db: Session = Depends(get_db)
):
    """Pause all running campaigns that depend on a specific service."""
    try:
        # Validate service name
        try:
            service = ThirdPartyService(request.service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {request.service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        # Import campaign service
        from app.services.campaign import CampaignService
        campaign_service = CampaignService()
        
        # Pause campaigns that depend on this service
        paused_count = await campaign_service.pause_campaigns_for_service(service, request.reason, db)
        
        return QueueStatusResponse(
            status="success",
            data={
                "service": service.value,
                "campaigns_paused": paused_count,
                "reason": request.reason,
                "message": f"Paused {paused_count} campaigns dependent on {service.value}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing campaigns for service {request.service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error pausing campaigns: {str(e)}"
        )

@router.post("/resume-campaigns-for-service", response_model=QueueStatusResponse)
async def resume_campaigns_for_service(
    request: BulkCampaignResumeRequest,
    db: Session = Depends(get_db)
):
    """Resume paused campaigns that were paused due to a specific service."""
    try:
        # Validate service name
        try:
            service = ThirdPartyService(request.service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {request.service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        # Import campaign service and models
        from app.services.campaign import CampaignService
        from app.models.campaign import Campaign, CampaignStatus
        
        campaign_service = CampaignService()
        
        # Get paused campaigns that were paused due to this service
        paused_campaigns = (
            db.query(Campaign)
            .filter(Campaign.status == CampaignStatus.PAUSED)
            .all()
        )
        
        # Filter campaigns paused due to this specific service
        service_paused_campaigns = []
        for campaign in paused_campaigns:
            if (campaign.status_message and 
                service.value.lower() in campaign.status_message.lower()):
                service_paused_campaigns.append(campaign)
        
        # Try to resume each campaign
        resumed_count = 0
        for campaign in service_paused_campaigns:
            try:
                # Check if campaign can be safely resumed
                can_start, reason = campaign_service.can_start_campaign(campaign)
                if campaign.status == CampaignStatus.PAUSED:
                    # For paused campaigns, check circuit breaker status
                    circuit_breaker = get_redis_connection()
                    cb_service = CircuitBreakerService(circuit_breaker)
                    
                    # Check if the specific service is available
                    allowed = cb_service.should_allow_request()
                    if allowed:
                        await campaign_service.resume_campaign(campaign.id, db)
                        resumed_count += 1
                        logger.info(f"Resumed campaign {campaign.id} after {service.value} recovery")
                    else:
                        logger.info(f"Cannot resume campaign {campaign.id}: {reason}")
                        
            except Exception as e:
                logger.error(f"Error resuming campaign {campaign.id}: {str(e)}")
                continue
        
        return QueueStatusResponse(
            status="success", 
            data={
                "service": service.value,
                "campaigns_eligible": len(service_paused_campaigns),
                "campaigns_resumed": resumed_count,
                "message": f"Resumed {resumed_count} of {len(service_paused_campaigns)} campaigns after {service.value} recovery"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming campaigns for service {request.service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming campaigns: {str(e)}"
        )

@router.get("/campaign-status", response_model=CampaignStatusResponse)
async def get_campaign_pause_status(db: Session = Depends(get_db)):
    """Get pause status for all campaigns organized by status and service dependency."""
    try:
        from app.models.campaign import Campaign, CampaignStatus
        
        # Get all campaigns
        all_campaigns = db.query(Campaign).all()
        
        # Organize campaigns by status - using UPPERCASE keys to match enum values
        status_summary = {
            "RUNNING": [],
            "PAUSED": [],
            "CREATED": [],
            "COMPLETED": [],
            "FAILED": []
        }
        
        # Service dependency analysis for paused campaigns
        service_pause_summary = {}
        
        for campaign in all_campaigns:
            campaign_data = {
                "id": campaign.id,
                "name": campaign.name,
                "status": campaign.status.value,  # This returns uppercase like "PAUSED"
                "status_message": campaign.status_message,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None
            }
            
            # Add to status summary using uppercase status key
            status_key = campaign.status.value  # "RUNNING", "PAUSED", etc.
            if status_key in status_summary:
                status_summary[status_key].append(campaign_data)
            
            # Analyze paused campaigns by service
            if campaign.status == CampaignStatus.PAUSED and campaign.status_message:
                # Try to extract service from status message
                for service in ThirdPartyService:
                    if service.value.lower() in campaign.status_message.lower():
                        if service.value not in service_pause_summary:
                            service_pause_summary[service.value] = []
                        service_pause_summary[service.value].append(campaign_data)
                        break
        
        # Calculate totals using uppercase keys
        totals = {
            "total_campaigns": len(all_campaigns),
            "RUNNING": len(status_summary["RUNNING"]),
            "PAUSED": len(status_summary["PAUSED"]),
            "CREATED": len(status_summary["CREATED"]),
            "COMPLETED": len(status_summary["COMPLETED"]),
            "FAILED": len(status_summary["FAILED"])
        }
        
        return CampaignStatusResponse(
            status="success",
            data=CampaignStatusData(
                totals=CampaignStatusTotals(**totals),
                campaigns_by_status=CampaignStatusSummary(**status_summary),
                paused_by_service=service_pause_summary,
                timestamp=None
            )
        )
        
    except Exception as e:
        logger.error(f"Error getting campaign pause status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting campaign status: {str(e)}"
        )

@router.get("/paused-campaigns/{service}", response_model=PausedCampaignsResponse)
async def get_paused_campaigns_for_service(
    service: str,
    db: Session = Depends(get_db)
):
    """Get campaigns that are paused due to a specific service failure."""
    try:
        # Validate service name
        try:
            service_enum = ThirdPartyService(service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        from app.models.campaign import Campaign, CampaignStatus
        
        # Get paused campaigns that mention this service in their status message
        paused_campaigns = (
            db.query(Campaign)
            .filter(Campaign.status == CampaignStatus.PAUSED)
            .all()
        )
        
        service_paused_campaigns = []
        for campaign in paused_campaigns:
            if (campaign.status_message and 
                service_enum.value.lower() in campaign.status_message.lower()):
                
                campaign_data = {
                    "id": campaign.id,
                    "name": campaign.name,
                    "status": campaign.status.value,  # Returns uppercase "PAUSED"
                    "status_message": campaign.status_message,
                    "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                    "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None
                }
                service_paused_campaigns.append(campaign_data)
        
        return PausedCampaignsResponse(
            status="success",
            data=PausedCampaignsData(
                service=service_enum.value,
                paused_campaigns=service_paused_campaigns,
                count=len(service_paused_campaigns),
                message=f"Found {len(service_paused_campaigns)} campaigns paused due to {service_enum.value} issues"
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paused campaigns for service {service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting paused campaigns: {str(e)}"
        )

@router.post("/circuit-breakers/{service}/reset", response_model=QueueStatusResponse)
async def reset_circuit_breaker(
    service: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """
    Reset circuit breaker (global) - service parameter is maintained for API compatibility but circuit breaker is now global.
    NOTE: This only closes the circuit breaker, it does NOT automatically resume campaigns.
    Use /resume-queue endpoint to resume paused campaigns after circuit breaker reset.
    """
    try:
        # Validate service name for API compatibility
        try:
            service_enum = ThirdPartyService(service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        # Reset circuit breaker (this is now global, not service-specific)
        current_state = queue_manager.circuit_breaker.get_global_circuit_state()
        
        if current_state.value == "closed":
            logger.info(f"Circuit breaker reset requested for {service_enum.value} but circuit breaker is already closed")
            return QueueStatusResponse(
                status="success",
                data={
                    "service": service_enum.value,
                    "action": "circuit_breaker_reset",
                    "circuit_breaker_state": "closed",
                    "message": f"Circuit breaker is already closed. No reset needed."
                }
            )
        
        # Manually close the circuit breaker
        closed = queue_manager.circuit_breaker.manually_close_circuit()
        
        if closed:
            logger.info(f"Circuit breaker reset completed (was requested for {service_enum.value})")
            return QueueStatusResponse(
                status="success",
                data={
                    "service": service_enum.value,
                    "action": "circuit_breaker_reset",
                    "circuit_breaker_state": "closed",
                    "message": f"Circuit breaker reset successful. Use /resume-queue to resume paused campaigns and jobs."
                }
            )
        else:
            logger.warning(f"Circuit breaker reset failed for {service_enum.value}")
            return QueueStatusResponse(
                status="error",
                data={
                    "service": service_enum.value,
                    "action": "circuit_breaker_reset",
                    "circuit_breaker_state": current_state.value,
                    "message": f"Circuit breaker reset failed. Current state: {current_state.value}"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting circuit breaker for {service}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting circuit breaker: {str(e)}"
        )

@router.post("/resume-queue", response_model=QueueStatusResponse)
async def resume_queue(
    queue_manager: QueueManager = Depends(get_queue_manager),
    db: Session = Depends(get_db)
):
    """
    Manually resume the entire queue system (NEW MANUAL RESUME LOGIC).
    
    This is the PRIMARY way to resume campaigns after circuit breaker events.
    Validates all circuit breakers are closed before resuming.
    
    Implements the cascade: Queue Resume → Campaign Resume → Job Resume
    """
    try:
        logger.info("Manual queue resume requested - validating prerequisites")
        
        # STEP 1: Validate ALL circuit breakers are closed (prerequisite check)
        redis_client = get_redis_connection()
        circuit_breaker = CircuitBreakerService(redis_client)
        
        blocked_services = []
        all_services = [
            ThirdPartyService.APOLLO,
            ThirdPartyService.PERPLEXITY,
            ThirdPartyService.OPENAI,
            ThirdPartyService.INSTANTLY,
            ThirdPartyService.MILLIONVERIFIER
        ]
        
        for service in all_services:
            allowed = circuit_breaker.should_allow_request()
            if not allowed:
                blocked_services.append(f"Global circuit breaker (open)")
                break  # Since it's global, if it's open, all services are blocked
        
        if blocked_services:
            error_message = f"Cannot resume queue: Circuit breakers still open for: {', '.join(blocked_services)}"
            logger.warning(error_message)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        logger.info("Prerequisites met: Global circuit breaker is closed - proceeding with queue resume")
        
        # STEP 2: Resume queue for all services
        total_jobs_resumed = 0
        
        # Since circuit breaker is global, we just need to resume jobs for all services
        # The circuit breaker is already closed at this point
        for service in all_services:
            # Resume jobs for each service
            jobs_resumed = queue_manager.resume_jobs_for_service(service)
            total_jobs_resumed += jobs_resumed
            
            logger.info(f"Queue resume: {jobs_resumed} jobs resumed for {service.value}")
        
        # STEP 3: Resume ALL paused campaigns (coordinated resume)
        from app.services.campaign import CampaignService
        from app.models.campaign import Campaign, CampaignStatus
        
        campaign_service = CampaignService()
        
        # Get ALL paused campaigns
        paused_campaigns = (
            db.query(Campaign)
            .filter(Campaign.status == CampaignStatus.PAUSED)
            .all()
        )
        
        campaigns_resumed = 0
        campaign_resume_errors = []
        
        for campaign in paused_campaigns:
            try:
                # Resume the campaign (all prerequisites are met)
                await campaign_service.resume_campaign(campaign.id, db)
                campaigns_resumed += 1
                logger.info(f"Queue resume: Campaign {campaign.id} resumed")
                
            except Exception as e:
                error_msg = f"Campaign {campaign.id}: {str(e)}"
                campaign_resume_errors.append(error_msg)
                logger.error(f"Error resuming campaign {campaign.id} during queue resume: {str(e)}")
        
        # STEP 4: Log the complete queue resume operation
        logger.info(f"Manual queue resume completed: {total_jobs_resumed} jobs, {campaigns_resumed} campaigns resumed")
        
        response_data = {
            "queue_resumed": True,
            "jobs_resumed": total_jobs_resumed,
            "campaigns_eligible": len(paused_campaigns),
            "campaigns_resumed": campaigns_resumed,
            "services_resumed": [service.value for service in all_services],
            "prerequisites_met": "Global circuit breaker closed",
            "message": f"Queue resumed successfully: {total_jobs_resumed} jobs and {campaigns_resumed} campaigns resumed"
        }
        
        # Include any campaign resume errors in response
        if campaign_resume_errors:
            response_data["campaign_resume_errors"] = campaign_resume_errors
            response_data["message"] += f" (with {len(campaign_resume_errors)} campaign errors)"
        
        return QueueStatusResponse(
            status="success",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during manual queue resume: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming queue: {str(e)}"
        )

@router.post("/close-circuit", response_model=QueueStatusResponse)
async def close_circuit_breaker(
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Manually close the global circuit breaker and resume all paused jobs."""
    try:
        circuit_breaker = queue_manager.circuit_breaker
        
        # Check current state
        current_state = circuit_breaker.get_global_circuit_state()
        
        if current_state.value == "closed":
            return QueueStatusResponse(
                status="success",
                data={
                    "circuit_breaker_state": "closed",
                    "message": "Circuit breaker is already closed",
                    "jobs_resumed": 0
                }
            )
        
        # Manually close circuit breaker (this will trigger job resume)
        closed = circuit_breaker.manually_close_circuit()
        
        if closed:
            # Get updated status
            status_data = queue_manager.get_queue_status()
            
            return QueueStatusResponse(
                status="success",
                data={
                    "circuit_breaker_state": "closed",
                    "message": "Circuit breaker closed successfully and jobs resumed",
                    "queue_status": status_data
                }
            )
        else:
            return QueueStatusResponse(
                status="success",
                data={
                    "circuit_breaker_state": current_state.value,
                    "message": "Circuit breaker was already closed",
                    "jobs_resumed": 0
                }
            )
        
    except Exception as e:
        logger.error(f"Error closing circuit breaker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error closing circuit breaker: {str(e)}"
        ) 