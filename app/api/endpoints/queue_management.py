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
        
        # Pause the service
        queue_manager.circuit_breaker.manually_pause_service(service, request.reason)
        
        # Pause related jobs
        paused_jobs = queue_manager.pause_jobs_for_service(service, request.reason)
        
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
                "message": f"Service {service.value} paused successfully: {paused_jobs} jobs and {paused_campaigns} campaigns affected"
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
    """Manually resume a service and its related queues and campaigns."""
    try:
        # Validate service name
        try:
            service = ThirdPartyService(request.service.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service name: {request.service}. Valid services: {[s.value for s in ThirdPartyService]}"
            )
        
        # Resume the service
        queue_manager.circuit_breaker.manually_resume_service(service)
        
        # Resume related jobs
        resumed_jobs = queue_manager.resume_jobs_for_service(service)
        
        # Resume related campaigns
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
        resumed_campaigns = 0
        for campaign in service_paused_campaigns:
            try:
                # Check if all required services are now available before resuming
                can_start, reason = campaign_service.can_start_campaign(campaign)
                if campaign.status == CampaignStatus.PAUSED:
                    # For paused campaigns, check if this specific service is now available
                    allowed, cb_reason = queue_manager.circuit_breaker.should_allow_request(service)
                    if allowed:
                        # Additional check: make sure ALL required services are available
                        all_services_available = True
                        required_services = [
                            ThirdPartyService.APOLLO,
                            ThirdPartyService.PERPLEXITY,
                            ThirdPartyService.OPENAI,
                            ThirdPartyService.INSTANTLY,
                            ThirdPartyService.MILLIONVERIFIER
                        ]
                        
                        for required_service in required_services:
                            service_allowed, _ = queue_manager.circuit_breaker.should_allow_request(required_service)
                            if not service_allowed:
                                all_services_available = False
                                break
                        
                        if all_services_available:
                            await campaign_service.resume_campaign(campaign.id, db)
                            resumed_campaigns += 1
                            logger.info(f"Resumed campaign {campaign.id} after {service.value} recovery")
                        else:
                            logger.info(f"Cannot resume campaign {campaign.id}: Other services still unavailable")
                    else:
                        logger.info(f"Cannot resume campaign {campaign.id}: {cb_reason}")
                        
            except Exception as e:
                logger.error(f"Error resuming campaign {campaign.id}: {str(e)}")
                continue
        
        return QueueStatusResponse(
            status="success",
            data={
                "service": service.value,
                "resumed": True,
                "jobs_resumed": resumed_jobs,
                "campaigns_eligible": len(service_paused_campaigns),
                "campaigns_resumed": resumed_campaigns,
                "message": f"Service {service.value} resumed successfully: {resumed_jobs} jobs and {resumed_campaigns} campaigns affected"
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
    """Get status of all circuit breakers."""
    try:
        redis_client = get_redis_connection()
        circuit_breaker = CircuitBreakerService(redis_client)
        
        status_data = circuit_breaker.get_circuit_status()
        
        return QueueStatusResponse(
            status="success",
            data={
                "circuit_breakers": status_data,
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
                    allowed, cb_reason = cb_service.should_allow_request(service)
                    if allowed:
                        await campaign_service.resume_campaign(campaign.id, db)
                        resumed_count += 1
                        logger.info(f"Resumed campaign {campaign.id} after {service.value} recovery")
                    else:
                        logger.info(f"Cannot resume campaign {campaign.id}: {cb_reason}")
                        
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