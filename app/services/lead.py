from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)

class LeadService:
    """Service for handling lead-related operations."""

    async def get_leads(self, db: Session, campaign_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            query = db.query(Lead)
            if campaign_id:
                query = query.filter(Lead.campaign_id == campaign_id)
            leads = query.all()
            return [lead.to_dict() for lead in leads]
        except SQLAlchemyError as e:
            logger.error(f"Error fetching leads: {str(e)}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching leads")

    async def get_lead(self, lead_id: str, db: Session) -> Dict[str, Any]:
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
            return lead.to_dict()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching lead: {str(e)}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching lead")

    async def create_lead(self, lead_data: LeadCreate, db: Session) -> Dict[str, Any]:
        try:
            # Check for duplicate lead (by email and campaign_id)
            existing_lead = db.query(Lead).filter(
                Lead.email == lead_data.email,
                Lead.campaign_id == lead_data.campaign_id
            ).first()
            if existing_lead:
                # Update existing lead
                for key, value in lead_data.dict(exclude_unset=True).items():
                    setattr(existing_lead, key, value)
                existing_lead.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(existing_lead)
                return existing_lead.to_dict()
            # Create new lead
            lead = Lead(
                **lead_data.dict(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
            return lead.to_dict()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating lead: {str(e)}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating lead")

    async def update_lead(self, lead_id: str, update_data: LeadUpdate, db: Session) -> Dict[str, Any]:
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
            for key, value in update_data.dict(exclude_unset=True).items():
                setattr(lead, key, value)
            lead.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(lead)
            return lead.to_dict()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error updating lead: {str(e)}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating lead")

    async def delete_lead(self, lead_id: str, db: Session) -> None:
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
            db.delete(lead)
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error deleting lead: {str(e)}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting lead") 