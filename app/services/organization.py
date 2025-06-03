from typing import Dict, Any, List, Optional, Tuple
import re
from html import escape
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from datetime import datetime

from app.models.organization import Organization
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.core.logger import get_logger

logger = get_logger(__name__)


class OrganizationService:
    """Service for managing organization business logic."""
    
    def get_campaign_count(self, org_id: str, db: Session) -> int:
        """Get the number of campaigns for an organization."""
        try:
            count = db.query(Campaign).filter(Campaign.organization_id == org_id).count()
            return count
        except Exception as e:
            logger.error(f'Error getting campaign count for organization {org_id}: {str(e)}')
            return 0
    
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

    def validate_organization_data(self, data: dict) -> Tuple[bool, str]:
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

    async def create_organization(self, org_data: OrganizationCreate, db: Session) -> Dict[str, Any]:
        """Create a new organization."""
        try:
            logger.info(f'Creating organization: {org_data.name}')
            
            # Convert Pydantic model to dict
            data = org_data.model_dump()
            
            # Sanitize input
            sanitized_data = self.sanitize_input(data)
            
            # Additional validation
            if not sanitized_data.get('name'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Name is required'
                )
            if len(sanitized_data['name'].strip()) < 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Name must be at least 3 characters long'
                )
            if not sanitized_data.get('description'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Description is required'
                )

            organization = Organization(
                name=sanitized_data['name'],
                description=sanitized_data.get('description')
            )
            
            db.add(organization)
            db.commit()
            db.refresh(organization)
            
            logger.info(f'Successfully created organization {organization.id}')
            return organization.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f'Error creating organization: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating organization: {str(e)}"
            )

    async def get_organization(self, org_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get a single organization by ID."""
        try:
            logger.info(f'Fetching organization {org_id}')
            
            organization = db.query(Organization).filter(Organization.id == org_id).first()
            if not organization:
                logger.warning(f'Organization {org_id} not found')
                return None
            
            logger.info(f'Successfully fetched organization {org_id}')
            return organization.to_dict()
            
        except Exception as e:
            logger.error(f'Error getting organization: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching organization: {str(e)}"
            )

    async def get_organizations(self, db: Session, skip: int = 0, limit: int = 100, search: str = None) -> List[Dict[str, Any]]:
        """Get organizations with optional pagination and search."""
        try:
            logger.info(f'Fetching organizations with skip={skip}, limit={limit}, search={search}')
            
            query = db.query(Organization)
            
            # Apply search filter if provided
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    Organization.name.ilike(search_term) | 
                    Organization.description.ilike(search_term)
                )
            
            # Apply pagination and ordering
            organizations = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()
            logger.info(f'Found {len(organizations)} organizations')
            
            return [org.to_dict() for org in organizations]
            
        except Exception as e:
            logger.error(f'Error getting organizations: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching organizations: {str(e)}"
            )

    async def count_organizations(self, db: Session, search: str = None) -> int:
        """Count total organizations with optional search filter."""
        try:
            logger.info(f'Counting organizations with search={search}')
            
            query = db.query(Organization)
            
            # Apply search filter if provided
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    Organization.name.ilike(search_term) | 
                    Organization.description.ilike(search_term)
                )
            
            count = query.count()
            logger.info(f'Total organizations count: {count}')
            
            return count
            
        except Exception as e:
            logger.error(f'Error counting organizations: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error counting organizations: {str(e)}"
            )

    async def update_organization(self, org_id: str, update_data: OrganizationUpdate, db: Session) -> Optional[Dict[str, Any]]:
        """Update organization properties."""
        try:
            logger.info(f'Updating organization {org_id}')
            
            organization = db.query(Organization).filter(Organization.id == org_id).first()
            if not organization:
                logger.warning(f'Organization {org_id} not found')
                return None
            
            # Convert Pydantic model to dict, excluding unset values
            data = update_data.model_dump(exclude_unset=True)
            
            # Sanitize input
            sanitized_data = self.sanitize_input(data)
            
            # Validate only the fields being updated
            is_valid, error_message = self.validate_organization_data(sanitized_data)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message
                )
            
            # Update only provided fields
            for field, value in sanitized_data.items():
                setattr(organization, field, value)
            
            db.commit()
            db.refresh(organization)
            
            logger.info(f'Successfully updated organization {org_id}')
            return organization.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f'Error updating organization: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating organization: {str(e)}"
            ) 