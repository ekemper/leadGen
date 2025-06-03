from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import math

from app.core.database import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse
from app.services.lead import LeadService
from pydantic import BaseModel

# Response models for consistent API structure
class LeadListData(BaseModel):
    leads: List[LeadResponse]
    total: int
    page: int
    per_page: int
    pages: int

class LeadsListResponse(BaseModel):
    status: str
    data: LeadListData

class LeadDetailResponse(BaseModel):
    status: str
    data: LeadResponse

class LeadCreateResponse(BaseModel):
    status: str
    data: LeadResponse

class LeadUpdateResponse(BaseModel):
    status: str
    data: LeadResponse

router = APIRouter()

@router.get("/", response_model=LeadsListResponse)
async def list_leads(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    db: Session = Depends(get_db)
):
    """List all leads with optional pagination and campaign filtering"""
    lead_service = LeadService()
    
    # Get all leads data first
    leads_data = await lead_service.get_leads(db, campaign_id=campaign_id)
    
    # Convert to response models
    all_leads = []
    for lead_dict in leads_data:
        lead = db.query(Lead).filter(Lead.id == lead_dict['id']).first()
        if lead:
            all_leads.append(LeadResponse(**lead.to_dict()))
    
    # Calculate pagination
    total_leads = len(all_leads)
    total_pages = math.ceil(total_leads / per_page) if total_leads > 0 else 1
    skip = (page - 1) * per_page
    
    # Apply pagination
    paginated_leads = all_leads[skip:skip + per_page]
    
    # Create response data
    data = LeadListData(
        leads=paginated_leads,
        total=total_leads,
        page=page,
        per_page=per_page,
        pages=total_pages
    )
    
    return LeadsListResponse(status="success", data=data)

@router.post("/", response_model=LeadCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_in: LeadCreate,
    db: Session = Depends(get_db)
):
    """Create a new lead"""
    lead_service = LeadService()
    lead_dict = await lead_service.create_lead(lead_in, db)
    lead = db.query(Lead).filter(Lead.id == lead_dict['id']).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lead created but could not be retrieved"
        )
    
    return LeadCreateResponse(
        status="success",
        data=LeadResponse(**lead.to_dict())
    )

@router.get("/{lead_id}", response_model=LeadDetailResponse)
async def get_lead(
    lead_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific lead by ID"""
    lead_service = LeadService()
    lead_dict = await lead_service.get_lead(lead_id, db)
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found"
        )
    
    return LeadDetailResponse(
        status="success",
        data=LeadResponse(**lead.to_dict())
    )

@router.put("/{lead_id}", response_model=LeadUpdateResponse)
async def update_lead(
    lead_id: str,
    lead_update: LeadUpdate,
    db: Session = Depends(get_db)
):
    """Update a specific lead by ID"""
    lead_service = LeadService()
    lead_dict = await lead_service.update_lead(lead_id, lead_update, db)
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found"
        )
    
    return LeadUpdateResponse(
        status="success",
        data=LeadResponse(**lead.to_dict())
    ) 