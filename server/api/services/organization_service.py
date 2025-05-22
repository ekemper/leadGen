from server.models.organization import Organization
from server.utils.logging_config import setup_logger, ContextLogger
from server.config.database import db
from typing import Dict, Any, List, Optional
import re
from html import escape

# Configure module logger
logger = setup_logger('organization_service')

class OrganizationService:
    """Service for managing organizations."""
    
    def __init__(self):
        """Initialize the organization service."""
        self.logger = logger

    def sanitize_input(self, data: dict) -> dict:
        """Sanitize input data to prevent XSS and other attacks."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Remove any HTML tags
                value = re.sub(r'<[^>]+>', '', value)
                # Escape HTML special characters
                value = escape(value)
                # Remove any control characters
                value = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', value)
                # Trim whitespace
                value = value.strip()
            sanitized[key] = value
        return sanitized

    def validate_organization_data(self, data: dict) -> tuple[bool, str]:
        """Validate organization data."""
        # Only validate fields that are present in the update
        if 'name' in data:
            if not data['name']:
                return False, 'Name is required'
            if len(data['name'].strip()) < 3:
                return False, 'Name must be at least 3 characters long'
        
        if 'description' in data:
            if not data['description']:
                return False, 'Description is required'
        
        return True, ''

    def create_organization(self, data: Dict[str, Any]) -> Organization:
        """Create a new organization."""
        with ContextLogger(self.logger):
            try:
                organization = Organization(
                    name=data['name'],
                    description=data.get('description'),
                    website=data.get('website'),
                    industry=data.get('industry')
                )
                db.session.add(organization)
                db.session.commit()
                
                self.logger.info(f"Created organization: {organization.name}")
                return organization
                
            except Exception as e:
                self.logger.error(f"Error creating organization: {str(e)}", exc_info=True)
                db.session.rollback()
                raise

    def get_organization(self, org_id):
        org = Organization.query.get(org_id)
        return org.to_dict() if org else None

    def get_organizations(self):
        orgs = Organization.query.all()
        return [org.to_dict() for org in orgs]

    def update_organization(self, org_id: int, data: Dict[str, Any]) -> Organization:
        """Update an existing organization."""
        with ContextLogger(self.logger, org_id=org_id):
            try:
                organization = Organization.query.get(org_id)
                if not organization:
                    raise ValueError(f"Organization {org_id} not found")
                
                # Update fields
                organization.name = data.get('name', organization.name)
                organization.description = data.get('description', organization.description)
                organization.website = data.get('website', organization.website)
                organization.industry = data.get('industry', organization.industry)
                
                db.session.commit()
                
                self.logger.info(f"Updated organization: {organization.name}")
                return organization
                
            except Exception as e:
                self.logger.error(f"Error updating organization: {str(e)}", exc_info=True)
                db.session.rollback()
                raise 