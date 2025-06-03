import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
import uuid

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.organization import Organization
from app.models.user import User
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.lead import Lead

# Import all campaign fixtures
from tests.fixtures.campaign_fixtures import *

# Override settings for testing
settings.POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
settings.POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
settings.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
settings.POSTGRES_DB = os.getenv("POSTGRES_DB", "test_db")

# Always use PostgreSQL for tests
SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    """Override the default database dependency."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override the dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test with transaction rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Begin a nested transaction
    session.begin_nested()
    
    # Override get_db to use this specific session
    def override_get_db_session():
        yield session
    
    app.dependency_overrides[get_db] = override_get_db_session
    
    yield session
    
    # Rollback the transaction
    session.close()
    transaction.rollback()
    connection.close()
    
    # Restore original override
    app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client that uses the test database session."""
    return TestClient(app)

@pytest.fixture(scope="function")
def test_db_session(db_session):
    """Alias for db_session for compatibility with existing tests."""
    return db_session

@pytest.fixture(autouse=True)
def cleanup_database():
    """Clean up database before each test."""
    # Import models to ensure they're registered
    from app.models.campaign import Campaign
    from app.models.job import Job
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.lead import Lead
    
    # Clean before test
    db = TestingSessionLocal()
    try:
        # Delete in correct order to respect foreign keys
        # Leads must be deleted before campaigns
        db.query(Lead).delete()
        db.query(Job).delete()
        db.query(Campaign).delete()
        db.query(Organization).delete()
        db.query(User).delete()  # Add user cleanup
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    
    yield
    
    # Clean after test (backup cleanup)
    db = TestingSessionLocal()
    try:
        # Delete in correct order to respect foreign keys
        # Leads must be deleted before campaigns
        db.query(Lead).delete()
        db.query(Job).delete()
        db.query(Campaign).delete()
        db.query(Organization).delete()
        db.query(User).delete()  # Add user cleanup
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

# Import database helpers fixtures
from tests.helpers.database_helpers import DatabaseHelpers

@pytest.fixture
def db_helpers(db_session):
    """Provide database helper utilities for tests."""
    return DatabaseHelpers(db_session)

@pytest.fixture(scope="function")
def organization(db_session):
    """Create and return a valid organization for use in tests."""
    org = Organization(
        id=str(uuid.uuid4()),
        name="Test Organization",
        description="Primary test organization"
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org

@pytest.fixture(scope="function")
def multiple_organizations(db_session):
    """Create multiple test organizations for variety testing."""
    orgs = []
    for i in range(3):
        org = Organization(
            id=str(uuid.uuid4()),
            name=f"Test Organization {i+1}",
            description=f"Test organization {i+1} for variety testing"
        )
        db_session.add(org)
        orgs.append(org)
    db_session.commit()
    for org in orgs:
        db_session.refresh(org)
    return orgs

# Authentication fixtures
from tests.helpers.auth_helpers import AuthHelpers

@pytest.fixture
def auth_helpers(db_session):
    """Provide authentication helper utilities for tests."""
    return AuthHelpers

@pytest.fixture
def test_user(db_session):
    """Create a test user for authentication."""
    return AuthHelpers.create_test_user(db_session)

@pytest.fixture
def authenticated_user(db_session):
    """Create a user and return user, token, and headers."""
    return AuthHelpers.create_authenticated_user(db_session)

@pytest.fixture
def authenticated_client(client, db_session):
    """Create an authenticated client with user, token, and headers."""
    user, token, headers = AuthHelpers.get_authenticated_client_data(client, db_session)
    
    # Create a wrapper that automatically includes auth headers
    class AuthenticatedClient:
        def __init__(self, client, headers, user, token):
            self.client = client
            self.headers = headers
            self.user = user
            self.token = token
        
        def get(self, url, **kwargs):
            kwargs.setdefault('headers', {}).update(self.headers)
            return self.client.get(url, **kwargs)
        
        def post(self, url, **kwargs):
            kwargs.setdefault('headers', {}).update(self.headers)
            return self.client.post(url, **kwargs)
        
        def patch(self, url, **kwargs):
            kwargs.setdefault('headers', {}).update(self.headers)
            return self.client.patch(url, **kwargs)
        
        def put(self, url, **kwargs):
            kwargs.setdefault('headers', {}).update(self.headers)
            return self.client.put(url, **kwargs)
        
        def delete(self, url, **kwargs):
            kwargs.setdefault('headers', {}).update(self.headers)
            return self.client.delete(url, **kwargs)
    
    return AuthenticatedClient(client, headers, user, token) 