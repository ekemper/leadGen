import os
import pytest
from flask import Flask
from dotenv import load_dotenv
from server.app import create_app
from server.config.database import db, init_db
from server.api.services.auth_service import AuthService
from server.utils.logging_config import LOG_DIR
from unittest.mock import MagicMock
from rq import Queue
from server.config.queue_config import QUEUE_CONFIG
from server.api.schemas import (
    ErrorResponseSchema, SuccessResponseSchema,
    CampaignSchema, JobSchema, LeadSchema,
    TokenSchema, UserSchema
)

# Set test environment
os.environ['FLASK_ENV'] = 'test'

# Define test secret key to be used consistently
TEST_SECRET_KEY = 'test-secret-key'

@pytest.fixture
def schemas():
    """Return schema instances for validation."""
    return {
        'error': ErrorResponseSchema(),
        'success': SuccessResponseSchema(),
        'campaign': CampaignSchema(),
        'job': JobSchema(),
        'lead': LeadSchema(),
        'token': TokenSchema(),
        'user': UserSchema()
    }

@pytest.fixture
def test_secret_key():
    """Return the test secret key."""
    return TEST_SECRET_KEY

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'RATELIMIT_ENABLED': False,  # Disable rate limiting for tests
        'SECRET_KEY': TEST_SECRET_KEY
    }
    
    app = create_app(test_config)
    
    # Create tables for test database
    with app.app_context():
        db.create_all()
    
    yield app
    
    # Clean up / reset resources
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

@pytest.fixture
def test_user():
    """Test user data."""
    return {
        'email': 'test@example.com',
        'password': 'Test1234!',
        'confirm_password': 'Test1234!'
    }

@pytest.fixture
def auth_headers(client, test_user):
    """Get auth headers for a test user."""
    # Register the user
    client.post('/api/auth/signup', json=test_user)
    
    # Login to get the token
    response = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']
    })
    
    token = response.json['data']['token']
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def db_session(app):
    """Database session fixture."""
    return db.session

@pytest.fixture
def clear_users(app, db_session):
    """Clear the users table before each test"""
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db_session.execute(table.delete())
        db_session.commit()

@pytest.fixture
def setup_logs():
    """Setup and cleanup log files before and after tests."""
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, mode=0o755)
    
    # Initialize log files with proper permissions
    log_files = ['browser.log']
    for log_file in log_files:
        log_path = os.path.join(LOG_DIR, log_file)
        # Create or truncate the file
        with open(log_path, 'w') as f:
            f.write('')  # Create empty file
        os.chmod(log_path, 0o666)  # Set read/write permissions for all
        
        # Verify the file is writable
        try:
            with open(log_path, 'a') as f:
                f.write('Test write\n')
            with open(log_path, 'r') as f:
                content = f.read()
                assert 'Test write' in content, f"Failed to write to {log_file}"
            # Clear the test content
            with open(log_path, 'w') as f:
                f.write('')
        except (IOError, AssertionError) as e:
            pytest.fail(f"Failed to setup log file {log_file}: {str(e)}")
    
    yield
    
    # Clean up log files after tests
    for log_file in log_files:
        log_path = os.path.join(LOG_DIR, log_file)
        try:
            if os.path.exists(log_path):
                os.remove(log_path)
        except OSError as e:
            print(f"Warning: Failed to remove log file {log_file}: {str(e)}")

@pytest.fixture
def mock_queue(monkeypatch):
    """Mock RQ queue for testing."""
    mock_queue = MagicMock(spec=Queue)
    mock_queue.enqueue.return_value = MagicMock(id='test-job-id')
    
    def mock_get_queue():
        return mock_queue
    
    monkeypatch.setattr('server.config.queue_config.get_queue', mock_get_queue)
    return mock_queue 