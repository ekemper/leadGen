from server.models import Organization
from server.config.database import db
from server.utils.logging_config import app_logger
import re
from html import escape

class OrganizationService:
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

    def create_organization(self, data):
        try:
            # Sanitize input
            sanitized_data = self.sanitize_input(data)
            
            # For creation, we require both fields
            if not sanitized_data.get('name'):
                raise ValueError('Name is required')
            if len(sanitized_data['name'].strip()) < 3:
                raise ValueError('Name must be at least 3 characters long')
            if not sanitized_data.get('description'):
                raise ValueError('Description is required')

            org = Organization(
                name=sanitized_data['name'],
                description=sanitized_data.get('description')
            )
            db.session.add(org)
            db.session.commit()
            return org.to_dict()
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Error creating organization: {str(e)}", extra={'component': 'server'})
            raise

    def get_organization(self, org_id):
        org = Organization.query.get(org_id)
        return org.to_dict() if org else None

    def get_organizations(self):
        orgs = Organization.query.all()
        return [org.to_dict() for org in orgs]

    def update_organization(self, org_id, data):
        try:
            # Sanitize input
            sanitized_data = self.sanitize_input(data)
            
            # Validate only the fields being updated
            is_valid, error_message = self.validate_organization_data(sanitized_data)
            if not is_valid:
                raise ValueError(error_message)

            org = Organization.query.get(org_id)
            if not org:
                return None

            if 'name' in sanitized_data:
                org.name = sanitized_data['name']
            if 'description' in sanitized_data:
                org.description = sanitized_data['description']

            db.session.commit()
            return org.to_dict()
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Error updating organization: {str(e)}", extra={'component': 'server'})
            raise 