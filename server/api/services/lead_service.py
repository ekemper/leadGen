from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid
from server.models import Lead
from server.config.database import db
from werkzeug.exceptions import BadRequest, NotFound
from server.utils.logging_config import app_logger as logger
from server.api.schemas import LeadSchema, LeadCreateSchema
from marshmallow import ValidationError

class LeadService:
    """Service for handling lead-related operations."""

    def __init__(self):
        self._ensure_transaction()

    def _ensure_transaction(self):
        """Ensure we have an active transaction."""
        if not db.session.is_active:
            db.session.begin()

    def get_leads(self, campaign_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all leads, optionally filtered by campaign.
        
        Args:
            campaign_id (str, optional): Campaign ID to filter by
            
        Returns:
            List[Dict[str, Any]]: List of leads
        """
        logger.info("Fetching leads")
        query = Lead.query
        if campaign_id:
            query = query.filter_by(campaign_id=campaign_id)
        leads = query.all()
        schema = LeadSchema(many=True)
        return schema.dump(leads)

    def get_lead(self, lead_id: str) -> Dict[str, Any]:
        """
        Get a specific lead by ID.
        
        Args:
            lead_id (str): Lead ID
            
        Returns:
            Dict[str, Any]: Lead data
            
        Raises:
            NotFound: If lead doesn't exist
        """
        logger.info(f"Fetching lead {lead_id}")
        lead = Lead.query.get(lead_id)
        if not lead:
            logger.warning(f"Lead {lead_id} not found")
            raise NotFound('Lead not found')
        
        schema = LeadSchema()
        return schema.dump(lead)

    def create_lead(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new lead.
        
        Args:
            data (Dict[str, Any]): Lead data
            
        Returns:
            Dict[str, Any]: Created lead data
            
        Raises:
            BadRequest: If data is invalid
        """
        try:
            # Validate input data
            schema = LeadCreateSchema()
            validated_data = schema.load(data)
            
            # Check for duplicate lead
            existing_lead = Lead.query.filter_by(
                email=validated_data['email'],
                campaign_id=validated_data['campaign_id']
            ).first()
            
            if existing_lead:
                # Update existing lead
                for key, value in validated_data.items():
                    setattr(existing_lead, key, value)
                existing_lead.updated_at = datetime.utcnow()
                db.session.commit()
                
                schema = LeadSchema()
                return schema.dump(existing_lead)
            
            # Create new lead
            lead = Lead(
                id=str(uuid.uuid4()),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **validated_data
            )
            db.session.add(lead)
            db.session.commit()
            
            schema = LeadSchema()
            return schema.dump(lead)
            
        except ValidationError as e:
            raise BadRequest(f"Invalid lead data: {e.messages}")

    def update_lead(self, lead_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a lead.
        
        Args:
            lead_id (str): Lead ID
            data (Dict[str, Any]): Updated lead data
            
        Returns:
            Dict[str, Any]: Updated lead data
            
        Raises:
            NotFound: If lead doesn't exist
            BadRequest: If data is invalid
        """
        logger.info(f"Updating lead {lead_id}")
        lead = Lead.query.get(lead_id)
        if not lead:
            logger.warning(f"Lead {lead_id} not found")
            raise NotFound('Lead not found')
        
        try:
            # Validate input data
            schema = LeadCreateSchema(partial=True)
            validated_data = schema.load(data)
            
            # Update lead
            for key, value in validated_data.items():
                setattr(lead, key, value)
            lead.updated_at = datetime.utcnow()
            db.session.commit()
            
            schema = LeadSchema()
            return schema.dump(lead)
            
        except ValidationError as e:
            raise BadRequest(f"Invalid lead data: {e.messages}")

    def delete_lead(self, lead_id: str) -> None:
        """
        Delete a lead.
        
        Args:
            lead_id (str): Lead ID
            
        Raises:
            NotFound: If lead doesn't exist
        """
        logger.info(f"Deleting lead {lead_id}")
        lead = Lead.query.get(lead_id)
        if not lead:
            logger.warning(f"Lead {lead_id} not found")
            raise NotFound('Lead not found')
        
        db.session.delete(lead)
        db.session.commit() 