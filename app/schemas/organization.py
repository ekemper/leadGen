from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    """Base organization schema with common fields."""
    name: str = Field(..., min_length=3, max_length=255, description="Organization name")
    description: str = Field(..., min_length=1, description="Organization description")


class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization."""
    pass


class OrganizationUpdate(BaseModel):
    """Schema for updating an existing organization."""
    name: Optional[str] = Field(None, min_length=3, max_length=255, description="Organization name")
    description: Optional[str] = Field(None, min_length=1, description="Organization description")


class OrganizationInDB(OrganizationBase):
    """Schema representing organization as stored in database."""
    id: str = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class OrganizationResponse(OrganizationInDB):
    """Schema for organization API responses."""
    campaign_count: int = Field(0, description="Number of campaigns in this organization")
    
    @classmethod
    def from_organization(cls, organization, campaign_count: int = 0):
        """Create response schema from organization model."""
        return cls(
            id=organization.id,
            name=organization.name,
            description=organization.description,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
            campaign_count=campaign_count
        ) 