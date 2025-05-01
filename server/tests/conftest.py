import os
import pytest
from flask import Flask
from dotenv import load_dotenv
from app import create_app
from config.database import db, init_db
from api.services.auth_service import AuthService

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'RATELIMIT_ENABLED': False,  # Disable rate limiting for tests
        'SECRET_KEY': 'test'
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
        'password': 'Test123!@#',
        'confirm_password': 'Test123!@#'
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
    
    token = response.json['token']
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def db_session(app):
    """Database session fixture."""
    return db.session

@pytest.fixture(autouse=True)
def clear_users(app, db_session):
    """Clear the users table before each test"""
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db_session.execute(table.delete())
        db_session.commit() 