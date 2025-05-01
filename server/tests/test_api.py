"""
Tests for API endpoints (health check and root endpoint).
"""
import pytest
from flask import json

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['message'] == 'API is running'
    assert data['endpoint'] == '/api/health'

def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get('/api/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Welcome to the Auth Template API'
    assert data['version'] == '1.0.0' 