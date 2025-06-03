from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import math

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate, 
    CampaignResponse, 
    CampaignUpdate, 
    CampaignStart,
    CampaignStatsResponse,
    InstantlyAnalyticsResponse
)
from app.services.campaign import CampaignService
from pydantic import BaseModel

# Custom response models to match frontend expectations
class CampaignListData(BaseModel):
    campaigns: List[CampaignResponse]
    total: int
    page: int
    per_page: int
    pages: int

class CampaignsListResponse(BaseModel):
    status: str
    data: CampaignListData

class CampaignDetailResponse(BaseModel):
    status: str
    data: CampaignResponse

class CampaignCreateResponse(BaseModel):
    status: str
    data: CampaignResponse

class CampaignUpdateResponse(BaseModel):
    status: str
    data: CampaignResponse

class CampaignDeleteResponse(BaseModel):
    status: str
    message: str

class CampaignStartResponse(BaseModel):
    status: str
    data: CampaignResponse

class CampaignPauseRequest(BaseModel):
    reason: str = "Manual pause requested"

class CampaignActionResponse(BaseModel):
    status: str
    message: str
    data: dict

class CampaignValidationResponse(BaseModel):
    status: str
    data: dict

router = APIRouter()

@router.get("/", response_model=CampaignsListResponse)
async def list_campaigns(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by campaign status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all campaigns with optional pagination and organization filtering"""
    campaign_service = CampaignService()
    
    # Get all campaigns data first
    campaigns_data = await campaign_service.get_campaigns(db, organization_id=organization_id)
    
    # Convert to response models
    all_campaigns = []
    for campaign_dict in campaigns_data:
        # Get the campaign object to create proper response
        campaign = db.query(Campaign).filter(Campaign.id == campaign_dict['id']).first()
        if campaign:
            campaign_response = CampaignResponse.from_campaign(campaign)
            # Apply status filter if provided
            if not status_filter or campaign_response.status == status_filter:
                all_campaigns.append(campaign_response)
    
    # Calculate pagination
    total_campaigns = len(all_campaigns)
    total_pages = math.ceil(total_campaigns / per_page) if total_campaigns > 0 else 1
    skip = (page - 1) * per_page
    
    # Apply pagination
    paginated_campaigns = all_campaigns[skip:skip + per_page]
    
    # Create response data
    data = CampaignListData(
        campaigns=paginated_campaigns,
        total=total_campaigns,
        page=page,
        per_page=per_page,
        pages=total_pages
    )
    
    return CampaignsListResponse(status="success", data=data)

@router.post("/", response_model=CampaignCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new campaign"""
    campaign_service = CampaignService()
    campaign_dict = await campaign_service.create_campaign(campaign_in, db)
    
    # Get the campaign object to create proper response
    campaign = db.query(Campaign).filter(Campaign.id == campaign_dict['id']).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Campaign created but could not be retrieved"
        )
    
    return CampaignCreateResponse(
        status="success",
        data=CampaignResponse.from_campaign(campaign)
    )

@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific campaign by ID"""
    campaign_service = CampaignService()
    campaign_dict = await campaign_service.get_campaign(campaign_id, db)
    
    # Get the campaign object to create proper response
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    return CampaignDetailResponse(
        status="success",
        data=CampaignResponse.from_campaign(campaign)
    )

@router.patch("/{campaign_id}", response_model=CampaignUpdateResponse)
async def update_campaign(
    campaign_id: str,
    campaign_update: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update campaign properties"""
    campaign_service = CampaignService()
    campaign_dict = await campaign_service.update_campaign(campaign_id, campaign_update, db)
    
    # Get the campaign object to create proper response
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    return CampaignUpdateResponse(
        status="success",
        data=CampaignResponse.from_campaign(campaign)
    )

@router.get("/{campaign_id}/start/validate", response_model=CampaignValidationResponse)
async def validate_campaign_start(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Validate if a campaign can be started without actually starting it"""
    campaign_service = CampaignService()
    
    # Get campaign
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    # Run validation
    validation_results = campaign_service.validate_campaign_start_prerequisites(campaign)
    
    return CampaignValidationResponse(
        status="success",
        data=validation_results
    )

@router.post("/{campaign_id}/start", response_model=CampaignStartResponse)
async def start_campaign(
    campaign_id: str,
    start_data: CampaignStart = CampaignStart(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Start campaign process"""
    campaign_service = CampaignService()
    campaign_dict = await campaign_service.start_campaign(campaign_id, start_data, db)
    
    # Get the campaign object to create proper response
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    return CampaignStartResponse(
        status="success",
        data=CampaignResponse.from_campaign(campaign)
    )

@router.post("/{campaign_id}/pause", response_model=CampaignActionResponse)
async def pause_campaign(
    campaign_id: str,
    pause_request: CampaignPauseRequest = CampaignPauseRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Pause a running campaign"""
    campaign_service = CampaignService()
    
    try:
        result = await campaign_service.pause_campaign(campaign_id, pause_request.reason, db)
        
        return CampaignActionResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error pausing campaign: {str(e)}"
        )

@router.post("/{campaign_id}/resume", response_model=CampaignActionResponse)
async def resume_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Resume a paused campaign"""
    campaign_service = CampaignService()
    
    try:
        result = await campaign_service.resume_campaign(campaign_id, db)
        
        return CampaignActionResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming campaign: {str(e)}"
        )

@router.get("/{campaign_id}/leads/stats", response_model=CampaignStatsResponse)
async def get_campaign_lead_stats(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get campaign lead statistics"""
    campaign_service = CampaignService()
    lead_stats = await campaign_service.get_campaign_lead_stats(campaign_id, db)
    
    return CampaignStatsResponse(
        status="success",
        data=lead_stats
    )

@router.get("/{campaign_id}/instantly/analytics", response_model=InstantlyAnalyticsResponse)
async def get_campaign_instantly_analytics(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get Instantly analytics for campaign"""
    campaign_service = CampaignService()
    instantly_analytics = await campaign_service.get_campaign_instantly_analytics(campaign_id, db)
    
    return InstantlyAnalyticsResponse(
        status="success",
        data=instantly_analytics
    )

@router.get("/{campaign_id}/details")
async def get_campaign_details(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get campaign details including lead stats and Instantly analytics"""
    campaign_service = CampaignService()
    
    # Get campaign
    campaign_dict = await campaign_service.get_campaign(campaign_id, db)
    
    # Get lead stats
    lead_stats = await campaign_service.get_campaign_lead_stats(campaign_id, db)
    
    # Get Instantly analytics
    instantly_analytics = await campaign_service.get_campaign_instantly_analytics(campaign_id, db)
    
    return {
        "status": "success",
        "data": {
            "campaign": campaign_dict,
            "lead_stats": lead_stats,
            "instantly_analytics": instantly_analytics
        }
    }

@router.post("/{campaign_id}/cleanup")
async def cleanup_campaign_jobs(
    campaign_id: str,
    cleanup_data: Dict[str, int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Clean up old jobs for a campaign"""
    if "days" not in cleanup_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days parameter is required"
        )
    
    days = cleanup_data["days"]
    if days <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be a positive integer"
        )
    
    campaign_service = CampaignService()
    result = await campaign_service.cleanup_campaign_jobs(campaign_id, days, db)
    
    return {
        "status": "success",
        "message": result["message"],
        "jobs_deleted": result.get("jobs_deleted", 0)
    }

@router.get("/{campaign_id}/results")
async def get_campaign_results(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get campaign results from completed jobs"""
    from app.models.job import Job, JobStatus
    
    # Get campaign
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    # Get completed jobs
    completed_jobs = (
        db.query(Job)
        .filter(
            Job.campaign_id == campaign_id,
            Job.status == JobStatus.COMPLETED
        )
        .all()
    )
    
    if not completed_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed jobs found for this campaign"
        )
    
    # Collect results from completed jobs
    results = {}
    for job in completed_jobs:
        # Note: Job result validation would be implemented in the Job model
        # For now, we'll include the results as-is
        results[job.name] = getattr(job, 'result', None)
    
    return {
        "status": "success",
        "data": {
            "campaign": campaign.to_dict(),
            "results": results
        }
    } 