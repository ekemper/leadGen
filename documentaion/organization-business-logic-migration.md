# Organization Business Logic Migration Guide

This document provides step-by-step instructions for migrating the organization business logic from the Flask-based leadGen application to the FastAPI-based fastapi-k8-proto application.

## Overview

The migration involves transferring:
- Organization model
- Organization service layer
- Organization API endpoints
- Functional API tests

Key principles:
- Preserve only business logic, not Flask-specific patterns
- Maintain FastAPI conventions and patterns
- Create comprehensive functional API tests
- Ensure database compatibility

## Prerequisites

Before starting the migration:
1. Ensure the FastAPI app is running properly
2. Database migrations are set up with Alembic
3. Test environment is configured

## Migration Steps

### Step 1: Create Organization Model

**Goal**: Create the Organization SQLAlchemy model following FastAPI patterns

**Actions**:
1. Create `app/models/organization.py`
2. Define the Organization model using SQLAlchemy declarative base
3. Include all fields from the original model
4. Add the `to_dict()` method for serialization
5. Update `app/models/__init__.py` to export the Organization model

**File to create**: `app/models/organization.py`

```python
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from typing import Dict, Any

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship to campaigns
    campaigns = relationship("Campaign", back_populates="organization")

    def to_dict(self) -> Dict[str, Any]:
        """Convert organization to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Organization {self.id}>'
```

**Update**: `app/models/__init__.py`
- Add: `from app.models.organization import Organization`
- Add to `__all__`: `"Organization"`

**Verification**:
```bash
python -c "from app.models import Organization; print('Organization model imported successfully')"
```

### Step 2: Update Campaign Model Relationship

**Goal**: Add the organization relationship to the Campaign model

**Actions**:
1. Update `app/models/campaign.py` to add the relationship

**File to update**: `app/models/campaign.py`
- Add import: `from sqlalchemy.orm import relationship`
- Add after the `jobs` relationship:
```python
# Relationship to organization
organization = relationship("Organization", back_populates="campaigns")
```

**Verification**:
```bash
python -c "from app.models import Campaign, Organization; print('Models with relationships imported successfully')"
```

### Step 3: Create Database Migration

**Goal**: Create and run Alembic migration for the organizations table

**Actions**:
1. Generate migration script
2. Review the generated migration
3. Run the migration

**Commands**:
```bash
# Generate migration
alembic revision --autogenerate -m "Add organizations table"

# Review the generated migration file in alembic/versions/

# Run migration
alembic upgrade head
```

**Verification**:
```bash
# Check if table exists
python -c "
from app.core.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print('organizations' in tables)
"
```

### Step 4: Create Organization Schemas

**Goal**: Create Pydantic schemas for request/response validation

**Actions**:
1. Create `app/schemas/organization.py`
2. Define schemas for create, update, and response

**File to create**: `app/schemas/organization.py`

```python
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
    pass
```

**Update**: `app/schemas/__init__.py`
- Add imports for organization schemas

**Verification**:
```bash
python -c "from app.schemas.organization import OrganizationCreate, OrganizationResponse; print('Schemas imported successfully')"
```

### Step 5: Create Organization Service

**Goal**: Create service layer with business logic

**Actions**:
1. Create `app/services/organization.py`
2. Implement all business logic methods
3. Include input sanitization and validation

**File to create**: `app/services/organization.py`

```python
from typing import Dict, Any, List, Optional, Tuple
import re
import logging
from html import escape
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


logger = logging.getLogger(__name__)


class OrganizationService:
    """Service for managing organization business logic."""
    
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
            data = org_data.dict()
            
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

    async def get_organizations(self, db: Session) -> List[Dict[str, Any]]:
        """Get all organizations."""
        try:
            logger.info('Fetching all organizations')
            
            organizations = db.query(Organization).order_by(Organization.created_at.desc()).all()
            logger.info(f'Found {len(organizations)} organizations')
            
            return [org.to_dict() for org in organizations]
            
        except Exception as e:
            logger.error(f'Error getting organizations: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching organizations: {str(e)}"
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
            data = update_data.dict(exclude_unset=True)
            
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
```

**Verification**:
```bash
python -c "from app.services.organization import OrganizationService; print('OrganizationService imported successfully')"
```

### Step 6: Create Organization API Endpoints

**Goal**: Create FastAPI router with all organization endpoints

**Actions**:
1. Create `app/api/endpoints/organizations.py`
2. Implement all CRUD endpoints
3. Add proper error handling and validation

**File to create**: `app/api/endpoints/organizations.py`

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.organization import Organization
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate
)
from app.services.organization import OrganizationService

router = APIRouter()

@router.get("/", response_model=List[OrganizationResponse])
async def list_organizations(
    db: Session = Depends(get_db)
):
    """Get all organizations"""
    organization_service = OrganizationService()
    organizations_data = await organization_service.get_organizations(db)
    
    # Convert to response models
    organizations = []
    for org_dict in organizations_data:
        org = db.query(Organization).filter(Organization.id == org_dict['id']).first()
        if org:
            organizations.append(OrganizationResponse.from_orm(org))
    
    return organizations

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
    
    return OrganizationResponse.from_orm(organization)

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
    return OrganizationResponse.from_orm(organization)

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
    return OrganizationResponse.from_orm(organization)
```

**Verification**:
```bash
python -c "from app.api.endpoints.organizations import router; print('Organizations router imported successfully')"
```

### Step 7: Register Organization Routes

**Goal**: Add organization routes to the main FastAPI application

**Actions**:
1. Update `app/main.py` to include organization routes

**File to update**: `app/main.py`
- Add import: `from app.api.endpoints import organizations`
- Add route registration after existing routes:
```python
app.include_router(
    organizations.router,
    prefix="/api/v1/organizations",
    tags=["organizations"]
)
```

**Verification**:
```bash
# Start the FastAPI server
uvicorn app.main:app --reload

# In another terminal, check if routes are registered
curl http://localhost:8000/openapi.json | grep organizations
```

### Step 8: Create Comprehensive API Tests

**Goal**: Create functional tests that hit the API and verify database state

**Actions**:
1. Create `tests/test_organizations_api.py`
2. Implement comprehensive test coverage
3. Test all CRUD operations and edge cases

**File to create**: `tests/test_organizations_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.main import app
from app.core.database import Base, get_db
from app.models.organization import Organization
from app.models.campaign import Campaign

# Test database
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost/test_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # Clean up test data after each test
        db.query(Campaign).delete()
        db.query(Organization).delete()
        db.commit()
        db.close()

@pytest.fixture
def organization_payload():
    """Return a valid payload for creating an organization via the API."""
    return {
        "name": "Test Organization",
        "description": "This is a test organization"
    }

def verify_organization_in_db(db_session, org_id: str, expected_data: dict = None):
    """Helper to verify organization exists in database with correct values."""
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    assert org is not None, f"Organization {org_id} not found in database"
    
    if expected_data:
        for key, value in expected_data.items():
            db_value = getattr(org, key)
            assert db_value == value, f"Expected {key}={value}, got {db_value}"
    
    return org

def verify_no_organization_in_db(db_session, org_id: str = None):
    """Helper to verify no organization records exist in database."""
    if org_id:
        org = db_session.query(Organization).filter(Organization.id == org_id).first()
        assert org is None, f"Organization {org_id} should not exist in database"
    else:
        count = db_session.query(Organization).count()
        assert count == 0, f"Expected 0 organizations in database, found {count}"

# ---------------------------------------------------------------------------
# Organization Creation Tests
# ---------------------------------------------------------------------------

def test_create_organization_success(db_session, organization_payload):
    """Test successful organization creation with all required fields."""
    response = client.post("/api/v1/organizations/", json=organization_payload)
    
    # Verify API response
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == organization_payload["name"]
    assert data["description"] == organization_payload["description"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    # Verify organization record exists in database with correct values
    verify_organization_in_db(db_session, data["id"], {
        "name": organization_payload["name"],
        "description": organization_payload["description"]
    })

def test_create_organization_validation_errors(db_session):
    """Test validation errors for invalid organization data."""
    # Test missing name
    response = client.post("/api/v1/organizations/", json={"description": "No name"})
    assert response.status_code == 422
    
    # Test short name
    response = client.post("/api/v1/organizations/", json={"name": "AB", "description": "Short name"})
    assert response.status_code == 422
    
    # Test missing description
    response = client.post("/api/v1/organizations/", json={"name": "Valid Name"})
    assert response.status_code == 422
    
    # Verify no database records created on validation failures
    verify_no_organization_in_db(db_session)

def test_create_organization_sanitization(db_session):
    """Test input sanitization for XSS prevention."""
    payload = {
        "name": "<script>alert('XSS')</script>Test Org",
        "description": "<img src=x onerror=alert('XSS')>Description"
    }
    response = client.post("/api/v1/organizations/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify HTML tags are removed
    assert "<script>" not in data["name"]
    assert "<img" not in data["description"]
    
    # Verify in database
    org = verify_organization_in_db(db_session, data["id"])
    assert "<script>" not in org.name
    assert "<img" not in org.description

def test_create_organization_special_characters(db_session):
    """Test organization creation with special characters."""
    payload = {
        "name": "Organization & Co. (Test) #1",
        "description": "Special chars: !@#$%^&*()_+-=[]{}|;:,.<>?/~`"
    }
    response = client.post("/api/v1/organizations/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify special characters are preserved (except HTML)
    verify_organization_in_db(db_session, data["id"], {
        "name": data["name"],
        "description": data["description"]
    })

# ---------------------------------------------------------------------------
# Organization Listing Tests
# ---------------------------------------------------------------------------

def test_list_organizations_empty(db_session):
    """Test empty organization list returns correctly."""
    response = client.get("/api/v1/organizations/")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    
    # Verify database is empty
    verify_no_organization_in_db(db_session)

def test_list_organizations_multiple(db_session, organization_payload):
    """Create multiple organizations and verify list endpoint returns all."""
    created_orgs = []
    
    # Create 3 organizations
    for i in range(3):
        payload = {**organization_payload, "name": f"Organization {i}"}
        response = client.post("/api/v1/organizations/", json=payload)
        assert response.status_code == 201
        created_orgs.append(response.json())
    
    # List organizations
    response = client.get("/api/v1/organizations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    
    # Verify all organizations are returned
    returned_ids = {org["id"] for org in data}
    expected_ids = {org["id"] for org in created_orgs}
    assert returned_ids == expected_ids
    
    # Verify database has all organizations
    db_count = db_session.query(Organization).count()
    assert db_count == 3

def test_list_organizations_order(db_session, organization_payload):
    """Test organizations are returned in correct order (newest first)."""
    # Create organizations with slight delay
    org_ids = []
    for i in range(3):
        payload = {**organization_payload, "name": f"Org {i}"}
        response = client.post("/api/v1/organizations/", json=payload)
        assert response.status_code == 201
        org_ids.append(response.json()["id"])
    
    # List organizations
    response = client.get("/api/v1/organizations/")
    assert response.status_code == 200
    data = response.json()
    
    # Verify newest first (reverse order of creation)
    returned_ids = [org["id"] for org in data]
    assert returned_ids == list(reversed(org_ids))

# ---------------------------------------------------------------------------
# Organization Retrieval Tests
# ---------------------------------------------------------------------------

def test_get_organization_success(db_session, organization_payload):
    """Test successful retrieval of existing organization."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    created_org = create_response.json()
    org_id = created_org["id"]
    
    # Retrieve organization
    response = client.get(f"/api/v1/organizations/{org_id}")
    assert response.status_code == 200
    data = response.json()
    
    # Verify returned data matches database record exactly
    assert data["id"] == org_id
    assert data["name"] == organization_payload["name"]
    assert data["description"] == organization_payload["description"]
    assert data["created_at"] == created_org["created_at"]
    assert data["updated_at"] == created_org["updated_at"]
    
    # Verify database record matches
    db_org = verify_organization_in_db(db_session, org_id)
    assert data["name"] == db_org.name
    assert data["description"] == db_org.description

def test_get_organization_not_found(db_session):
    """Test 404 error for non-existent organization ID."""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/organizations/{non_existent_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

def test_get_organization_malformed_id(db_session):
    """Test malformed organization ID handling."""
    malformed_id = "not-a-valid-uuid"
    response = client.get(f"/api/v1/organizations/{malformed_id}")
    
    # Should return 404 (not found) rather than 400 (bad request)
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Organization Update Tests
# ---------------------------------------------------------------------------

def test_update_organization_success(db_session, organization_payload):
    """Test successful update of organization fields."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    
    # Update organization
    update_data = {
        "name": "Updated Organization Name",
        "description": "Updated description"
    }
    response = client.put(f"/api/v1/organizations/{org_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    
    # Verify database record is updated correctly
    verify_organization_in_db(db_session, org_id, {
        "name": update_data["name"],
        "description": update_data["description"]
    })

def test_update_organization_partial(db_session, organization_payload):
    """Test partial updates work correctly."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    original_name = create_response.json()["name"]
    
    # Update only description
    update_data = {"description": "Only description updated"}
    response = client.put(f"/api/v1/organizations/{org_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == original_name  # Should remain unchanged
    assert data["description"] == update_data["description"]
    
    # Verify database record
    verify_organization_in_db(db_session, org_id, {
        "name": original_name,
        "description": update_data["description"]
    })

def test_update_organization_validation_errors(db_session, organization_payload):
    """Test validation errors for invalid update data."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    
    # Try to update with invalid data
    invalid_updates = [
        {"name": "AB"},  # Too short
        {"name": ""},    # Empty
        {"description": ""}  # Empty description
    ]
    
    for invalid_update in invalid_updates:
        response = client.put(f"/api/v1/organizations/{org_id}", json=invalid_update)
        assert response.status_code in [400, 422]
    
    # Verify database record is unchanged
    verify_organization_in_db(db_session, org_id, {
        "name": organization_payload["name"],
        "description": organization_payload["description"]
    })

def test_update_organization_not_found(db_session):
    """Test 404 error for non-existent organization."""
    non_existent_id = str(uuid.uuid4())
    update_data = {"name": "Updated Name"}
    response = client.put(f"/api/v1/organizations/{non_existent_id}", json=update_data)
    
    assert response.status_code == 404

def test_update_organization_sanitization(db_session, organization_payload):
    """Test input sanitization on updates."""
    # Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    
    # Update with HTML content
    update_data = {
        "name": "<b>Bold</b> Organization",
        "description": "<script>alert('XSS')</script>Description"
    }
    response = client.put(f"/api/v1/organizations/{org_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify HTML is sanitized
    assert "<b>" not in data["name"]
    assert "<script>" not in data["description"]

# ---------------------------------------------------------------------------
# Organization-Campaign Relationship Tests
# ---------------------------------------------------------------------------

def test_organization_with_campaigns(db_session, organization_payload):
    """Test organization relationship with campaigns."""
    # Create organization
    org_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]
    
    # Create campaign linked to organization
    campaign_payload = {
        "name": "Test Campaign",
        "description": "Campaign for org test",
        "organization_id": org_id,
        "fileName": "test.csv",
        "totalRecords": 100,
        "url": "https://app.apollo.io/test"
    }
    campaign_response = client.post("/api/v1/campaigns/", json=campaign_payload)
    assert campaign_response.status_code == 201
    
    # Verify campaign is linked to organization
    campaign_data = campaign_response.json()
    assert campaign_data["organization_id"] == org_id
    
    # Verify in database
    db_campaign = db_session.query(Campaign).filter(Campaign.id == campaign_data["id"]).first()
    assert db_campaign.organization_id == org_id

# ---------------------------------------------------------------------------
# Edge Cases and Error Handling Tests
# ---------------------------------------------------------------------------

def test_concurrent_organization_creation(db_session, organization_payload):
    """Test handling of concurrent organization creation."""
    # This test simulates race conditions by creating organizations rapidly
    import threading
    results = []
    
    def create_org(index):
        payload = {**organization_payload, "name": f"Concurrent Org {index}"}
        response = client.post("/api/v1/organizations/", json=payload)
        results.append(response.status_code)
    
    # Create 5 organizations concurrently
    threads = []
    for i in range(5):
        t = threading.Thread(target=create_org, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # All should succeed
    assert all(status == 201 for status in results)
    
    # Verify all 5 organizations exist in database
    db_count = db_session.query(Organization).count()
    assert db_count == 5

def test_sql_injection_prevention(db_session):
    """Test SQL injection prevention in organization operations."""
    # Try SQL injection in organization name
    malicious_payload = {
        "name": "Org'; DROP TABLE organizations; --",
        "description": "Normal description"
    }
    response = client.post("/api/v1/organizations/", json=malicious_payload)
    
    # Should succeed without executing SQL
    assert response.status_code == 201
    
    # Verify organizations table still exists
    db_count = db_session.query(Organization).count()
    assert db_count == 1
    
    # Try SQL injection in GET request
    malicious_id = "'; DROP TABLE organizations; --"
    response = client.get(f"/api/v1/organizations/{malicious_id}")
    assert response.status_code == 404
    
    # Verify table still exists
    db_count = db_session.query(Organization).count()
    assert db_count == 1

def test_organization_workflow_integration(db_session, organization_payload):
    """Test complete organization workflow: create, read, update, list."""
    # Step 1: Create organization
    create_response = client.post("/api/v1/organizations/", json=organization_payload)
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]
    
    # Step 2: Read organization
    get_response = client.get(f"/api/v1/organizations/{org_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == org_id
    
    # Step 3: Update organization
    update_data = {"name": "Updated via Workflow"}
    update_response = client.put(f"/api/v1/organizations/{org_id}", json=update_data)
    assert update_response.status_code == 200
    assert update_response.json()["name"] == update_data["name"]
    
    # Step 4: List organizations
    list_response = client.get("/api/v1/organizations/")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == org_id
    
    # Verify final state in database
    verify_organization_in_db(db_session, org_id, {
        "name": update_data["name"],
        "description": organization_payload["description"]
    })
```

**Verification**:
```bash
# Run the tests
pytest tests/test_organizations_api.py -v
```

### Step 9: Run Full Integration Test

**Goal**: Verify the complete organization functionality works end-to-end

**Actions**:
1. Start the FastAPI server
2. Run all organization tests
3. Verify API endpoints via curl

**Commands**:
```bash
# Terminal 1: Start the server
uvicorn app.main:app --reload

# Terminal 2: Run tests
pytest tests/test_organizations_api.py -v

# Terminal 3: Manual API verification
# Create organization
curl -X POST http://localhost:8000/api/v1/organizations/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Organization", "description": "Test Description"}'

# List organizations
curl http://localhost:8000/api/v1/organizations/

# Get specific organization (use ID from create response)
curl http://localhost:8000/api/v1/organizations/{org_id}

# Update organization
curl -X PUT http://localhost:8000/api/v1/organizations/{org_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Organization"}'
```

### Step 10: Final Verification Checklist

**Goal**: Ensure all components are properly integrated

**Verification Steps**:

1. **Model Integration**:
   - [ ] Organization model is created and imported
   - [ ] Relationship with Campaign model is established
   - [ ] Database migration is applied successfully

2. **Service Layer**:
   - [ ] OrganizationService handles all business logic
   - [ ] Input sanitization is working
   - [ ] Validation rules are enforced

3. **API Layer**:
   - [ ] All CRUD endpoints are accessible
   - [ ] Proper HTTP status codes are returned
   - [ ] Error responses follow FastAPI patterns

4. **Testing**:
   - [ ] All tests pass
   - [ ] Database state is verified in tests
   - [ ] Edge cases are covered

5. **Documentation**:
   - [ ] API documentation is available at `/docs`
   - [ ] All endpoints are properly documented
   - [ ] Request/response schemas are visible

## Troubleshooting

### Common Issues and Solutions

1. **Import Errors**:
   - Ensure all `__init__.py` files are updated
   - Check Python path includes the project root

2. **Database Errors**:
   - Run `alembic upgrade head` to apply migrations
   - Check database connection string in `.env`

3. **Test Failures**:
   - Ensure test database is separate from development
   - Clean up test data between runs

4. **API 422 Errors**:
   - Check request payload matches schema exactly
   - Verify all required fields are included

## Next Steps

After completing this migration:

1. Add authentication/authorization if needed
2. Implement additional business logic features
3. Add more comprehensive logging
4. Set up monitoring and metrics
5. Consider adding caching for performance

## Conclusion

This migration guide provides a systematic approach to transferring the organization business logic from Flask to FastAPI while maintaining clean architecture and comprehensive testing. Each step is designed to be independently verifiable, ensuring a smooth migration process. 