"""
Tests for JWT authentication middleware.
"""
import pytest
from datetime import datetime, timedelta
import jwt
from flask import json

def test_protected_endpoint_no_token(client):
    """Test accessing protected endpoint without token."""
    response = client.get('/api/leads')
    assert response.status_code == 401
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'Token is missing'

def test_protected_endpoint_invalid_token(client):
    """Test accessing protected endpoint with invalid token."""
    headers = {'Authorization': 'Bearer invalid_token'}
    response = client.get('/api/leads', headers=headers)
    assert response.status_code == 401
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'Invalid token'

def test_protected_endpoint_expired_token(client, auth_headers, test_secret_key):
    """Test accessing protected endpoint with expired token."""
    # Create an expired token
    expired_token = jwt.encode(
        {'user_id': 1, 'exp': datetime.utcnow() - timedelta(hours=1)},
        test_secret_key,
        algorithm='HS256'
    )
    headers = {'Authorization': f'Bearer {expired_token}'}
    response = client.get('/api/leads', headers=headers)
    assert response.status_code == 401
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'Token has expired'

def test_protected_endpoint_malformed_token(client):
    """Test accessing protected endpoint with malformed token."""
    headers = {'Authorization': 'Bearer'}
    response = client.get('/api/leads', headers=headers)
    assert response.status_code == 401
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'Token is missing'

def test_protected_endpoint_wrong_token_format(client):
    """Test accessing protected endpoint with wrong token format."""
    headers = {'Authorization': 'Basic invalid_token'}
    response = client.get('/api/leads', headers=headers)
    assert response.status_code == 401
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'Token is missing'

def test_protected_endpoint_valid_token(client, auth_headers):
    """Test accessing protected endpoint with valid token."""
    response = client.get('/api/leads', headers=auth_headers)
    assert response.status_code == 200

def test_protected_endpoint_user_not_found(client, test_secret_key):
    """Test accessing protected endpoint with token for non-existent user."""
    # Create token for non-existent user
    token = jwt.encode(
        {'user_id': 999999, 'exp': datetime.utcnow() + timedelta(days=1)},
        test_secret_key,
        algorithm='HS256'
    )
    headers = {'Authorization': f'Bearer {token}'}
    response = client.get('/api/leads', headers=headers)
    assert response.status_code == 401
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'User not found' 