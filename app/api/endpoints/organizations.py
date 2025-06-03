from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import math

from app.core.database import get_db
from app.models.organization import Organization
from app.models.campaign import Campaign
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate
)
from app.schemas.campaign import CampaignResponse
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.services.organization import OrganizationService
from app.services.campaign import CampaignService

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[OrganizationResponse])
async def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str = Query(None, description="Search term"),
    db: Session = Depends(get_db)
):
    """Get all organizations with pagination"""
    organization_service = OrganizationService()
    
    # Get total count first
    total_organizations = await organization_service.count_organizations(db, search=search)
    
    # Calculate pagination
    total_pages = math.ceil(total_organizations / limit) if total_organizations > 0 else 1
    skip = (page - 1) * limit
    
    # Get organizations data with pagination
    organizations_data = await organization_service.get_organizations(
        db, skip=skip, limit=limit, search=search
    )
    
    # Convert to response models with campaign counts
    organizations = []
    for org_dict in organizations_data:
        org = db.query(Organization).filter(Organization.id == org_dict['id']).first()
        if org:
            campaign_count = organization_service.get_campaign_count(org.id, db)
            organizations.append(OrganizationResponse.from_organization(org, campaign_count))
    
    # Create pagination metadata
    meta = PaginationMeta(
        page=page,
        limit=limit,
        total=total_organizations,
        pages=total_pages
    )
    
    return PaginatedResponse(data=organizations, meta=meta)

@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_in: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create a new organization"""
    organization_service = OrganizationService()
    org_dict = await organization_service.create_organization(organization_in, db)
    
    # Get the organization object to create proper response
    organization = db.query(Organization).filter(Organization.id == org_dict['id']).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Organization created but could not be retrieved"
        )
    
    # Get campaign count for the new organization (should be 0)
    campaign_count = organization_service.get_campaign_count(organization.id, db)
    return OrganizationResponse.from_organization(organization, campaign_count)

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific organization by ID"""
    organization_service = OrganizationService()
    org_dict = await organization_service.get_organization(org_id, db)
    
    if not org_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found"
        )
    
    # Get the organization object to create proper response
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    campaign_count = organization_service.get_campaign_count(org_id, db)
    return OrganizationResponse.from_organization(organization, campaign_count)

@router.get("/{org_id}/campaigns", response_model=List[CampaignResponse])
async def list_organization_campaigns(
    org_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all campaigns for a specific organization"""
    # Verify organization exists
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found"
        )
    
    # Get campaigns for this organization using the campaign service
    campaign_service = CampaignService()
    campaigns_data = await campaign_service.get_campaigns(db, organization_id=org_id)
    
    # Convert to response models and apply pagination
    campaigns = []
    for campaign_dict in campaigns_data:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_dict['id']).first()
        if campaign:
            campaigns.append(CampaignResponse.from_campaign(campaign))
    
    # Apply pagination
    return campaigns[skip:skip + limit]

@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    organization_update: OrganizationUpdate,
    db: Session = Depends(get_db)
):
    """Update organization properties"""
    organization_service = OrganizationService()
    org_dict = await organization_service.update_organization(org_id, organization_update, db)
    
    if not org_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found"
        )
    
    # Get the organization object to create proper response
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    campaign_count = organization_service.get_campaign_count(org_id, db)
    return OrganizationResponse.from_organization(organization, campaign_count) 