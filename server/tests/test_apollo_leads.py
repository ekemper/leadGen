"""
Tests for Apollo leads endpoint.
"""
import pytest
from flask import json

@pytest.fixture
def apollo_params():
    """Test Apollo parameters."""
    return {
        'fileName': 'https://apollo.io/search',
        'totalRecords': 10,
        'url': 'https://apollo.io/search'
    }

def test_fetch_apollo_leads_success(client, auth_headers, apollo_params):
    """Test successful Apollo leads fetch."""
    response = client.post('/api/fetch_apollo_leads', json=apollo_params, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['status'] == 'success'

def test_fetch_apollo_leads_missing_params(client, auth_headers):
    """Test Apollo leads fetch with missing parameters."""
    params = {
    }
    response = client.post('/api/fetch_apollo_leads', json=params, headers=auth_headers)
    assert response.status_code == 400
    assert 'Missing required parameter' in response.json['message']

def test_fetch_apollo_leads_invalid_params(client, auth_headers):
    """Test Apollo leads fetch with invalid parameters."""
    params = {
        'fileName': 'not-a-url',
        'totalRecords': 10,
        'url': 'not-a-url'
    }
    response = client.post('/api/fetch_apollo_leads', json=params, headers=auth_headers)
    assert response.status_code == 400

def test_fetch_apollo_leads_invalid_count(client, auth_headers, apollo_params):
    """Test Apollo leads fetch with invalid count."""
    params = apollo_params.copy()
    response = client.post('/api/fetch_apollo_leads', json=params, headers=auth_headers)
    assert response.status_code == 400
    assert 'count' in response.json['message'].lower()

def test_fetch_apollo_leads_invalid_url(client, auth_headers, apollo_params):
    """Test Apollo leads fetch with invalid search URL."""
    params = apollo_params.copy()
    params['fileName'] = 'not-a-url'
    response = client.post('/api/fetch_apollo_leads', json=params, headers=auth_headers)
    assert response.status_code == 400
    assert 'url' in response.json['message'].lower()

def test_fetch_apollo_leads_empty_params(client, auth_headers):
    """Test Apollo leads fetch with empty parameters."""
    response = client.post('/api/fetch_apollo_leads', json={}, headers=auth_headers)
    assert response.status_code == 400
    assert 'Missing required parameter' in response.json['message']

def test_fetch_apollo_leads_invalid_json(client, auth_headers):
    """Test Apollo leads fetch with invalid JSON payload."""
    response = client.post('/api/fetch_apollo_leads', 
        data='invalid json',
        headers=auth_headers,
        content_type='application/json'
    )
    assert response.status_code == 400
    assert 'Invalid JSON payload' in response.json['error'] 