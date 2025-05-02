from datetime import datetime
import uuid
from models import Lead
from config.database import db
from werkzeug.exceptions import BadRequest, NotFound

class LeadService:
    """Service for handling lead-related operations."""

    def get_leads(self, user_id: str) -> list:
        """
        Get all leads for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            list: List of leads
        """
        leads = Lead.query.filter_by(user_id=user_id).all()
        return [lead.to_dict() for lead in leads]

    def get_lead(self, user_id: str, lead_id: str) -> dict:
        """
        Get a specific lead.
        
        Args:
            user_id: The ID of the user
            lead_id: The ID of the lead
            
        Returns:
            dict: Lead data
            
        Raises:
            NotFound: If the lead doesn't exist
        """
        lead = Lead.query.filter_by(id=lead_id, user_id=user_id).first()
        if not lead:
            raise NotFound("Lead not found")
        return lead.to_dict()

    def create_lead(self, user_id: str, data: dict) -> dict:
        """
        Create a new lead.
        
        Args:
            user_id: The ID of the user
            data: Lead data
            
        Returns:
            dict: Created lead data
            
        Raises:
            BadRequest: If required fields are missing
        """
        required_fields = ['email', 'name', 'company']
        for field in required_fields:
            if not data.get(field):
                raise BadRequest(f"{field.capitalize()} is required for lead creation")

        # Check for duplicate
        existing_lead = Lead.query.filter_by(
            user_id=user_id,
            email=data['email']
        ).first()

        if existing_lead:
            return {
                'status': 'warning',
                'message': 'Lead with this email already exists',
                'data': existing_lead.to_dict()
            }

        lead = Lead(
            id=str(uuid.uuid4()),
            user_id=user_id,
            email=data['email'],
            name=data['name'],
            company=data['company'],
            notes=data.get('notes', ''),
            status=data.get('status', 'new'),
            phone=data.get('phone', ''),
            source=data.get('source', 'apollo'),
            campaign_id=data.get('campaign_id'),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.session.add(lead)
        db.session.commit()

        return lead.to_dict()

    def update_lead(self, user_id: str, lead_id: str, data: dict) -> dict:
        """
        Update a lead.
        
        Args:
            user_id: The ID of the user
            lead_id: The ID of the lead
            data: Updated lead data
            
        Returns:
            dict: Updated lead data
            
        Raises:
            NotFound: If the lead doesn't exist
        """
        lead = Lead.query.filter_by(id=lead_id, user_id=user_id).first()
        if not lead:
            raise NotFound("Lead not found")

        # Update fields
        for field in ['name', 'company', 'email', 'notes', 'status']:
            if field in data:
                setattr(lead, field, data[field])

        lead.updated_at = datetime.utcnow()
        db.session.commit()

        return lead.to_dict()

    # def delete_lead(self, user_id: str, lead_id: str) -> bool:
    #     """
    #     Delete a lead.
        
    #     Args:
    #         user_id: The ID of the user
    #         lead_id: The ID of the lead
            
    #     Returns:
    #         bool: True if deleted, False if not found
    #     """
    #     lead = Lead.query.filter_by(id=lead_id, user_id=user_id).first()
    #     if not lead:
    #         return False

    #     db.session.delete(lead)
    #     db.session.commit()
    #     return True 