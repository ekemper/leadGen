"""
Tests for leads endpoints.
"""
import pytest
from flask import json

@pytest.fixture
def lead_data():
    """Test lead data."""
    return {
        'name': 'Test Lead',
        'email': 'lead@example.com',
        'company': 'Test Company',
        'phone': '+1234567890',
        'status': 'new',
        'source': 'apollo',
        'notes': 'Test notes'
    }

def test_get_leads_success(client, auth_headers):
    """Test successful retrieval of all leads."""
    response = client.get('/api/leads', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert isinstance(response.json['data'], list)

def test_create_lead_success(client, auth_headers, lead_data):
    """Test successful lead creation."""
    response = client.post('/api/leads', json=lead_data, headers=auth_headers)
    assert response.status_code == 201
    assert response.json['status'] == 'success'
    assert response.json['data']['email'] == lead_data['email']
    assert response.json['data']['name'] == lead_data['name']
    assert response.json['data']['company'] == lead_data['company']

def test_create_lead_duplicate(client, auth_headers, lead_data):
    """Test creating a duplicate lead."""
    # Create first lead
    client.post('/api/leads', json=lead_data, headers=auth_headers)
    # Try to create duplicate
    response = client.post('/api/leads', json=lead_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['status'] == 'warning'
    assert 'already exists' in response.json['message']

def test_create_lead_missing_required_fields(client, auth_headers):
    """Test creating a lead with missing required fields."""
    # Test missing email
    response = client.post('/api/leads', json={
        'name': 'Test Lead',
        'company': 'Test Company'
    }, headers=auth_headers)
    assert response.status_code == 400
    assert 'Email is required' in response.json['message']

def test_get_lead_success(client, auth_headers, lead_data):
    """Test successful retrieval of a specific lead."""
    # First create a lead
    create_response = client.post('/api/leads', json=lead_data, headers=auth_headers)
    lead_id = create_response.json['data']['guid']
    
    # Then retrieve it
    response = client.get(f'/api/leads/{lead_id}', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['email'] == lead_data['email']

def test_get_lead_not_found(client, auth_headers):
    """Test retrieving a non-existent lead."""
    response = client.get('/api/leads/nonexistent', headers=auth_headers)
    assert response.status_code == 404
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'Lead not found'

def test_update_lead_success(client, auth_headers, lead_data):
    """Test successful lead update."""
    # First create a lead
    create_response = client.post('/api/leads', json=lead_data, headers=auth_headers)
    lead_id = create_response.json['data']['guid']
    
    # Then update it
    update_data = {'name': 'Updated Name', 'status': 'contacted'}
    response = client.put(f'/api/leads/{lead_id}', json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['name'] == update_data['name']
    assert response.json['data']['status'] == update_data['status']

def test_update_lead_not_found(client, auth_headers):
    """Test updating a non-existent lead."""
    response = client.put('/api/leads/nonexistent', json={'name': 'Updated'}, headers=auth_headers)
    assert response.status_code == 404
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'Lead not found'

def test_delete_lead_success(client, auth_headers, lead_data):
    """Test successful lead deletion."""
    # First create a lead
    create_response = client.post('/api/leads', json=lead_data, headers=auth_headers)
    lead_id = create_response.json['data']['guid']
    
    # Then delete it
    response = client.delete(f'/api/leads/{lead_id}', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['message'] == 'Lead deleted successfully'
    
    # Verify it's deleted
    get_response = client.get(f'/api/leads/{lead_id}', headers=auth_headers)
    assert get_response.status_code == 404

def test_delete_lead_not_found(client, auth_headers):
    """Test deleting a non-existent lead."""
    response = client.delete('/api/leads/nonexistent', headers=auth_headers)
    assert response.status_code == 404
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'Lead not found'

def test_invalid_json_payload(client, auth_headers):
    """Test handling of invalid JSON payloads."""
    response = client.post('/api/leads', 
        data='invalid json',
        headers=auth_headers,
        content_type='application/json'
    )
    assert response.status_code == 400
    assert 'Invalid JSON payload' in response.json['error'] 