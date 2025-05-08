"""
Tests for leads endpoints.
"""
import pytest
from flask import json
from datetime import datetime
from server.models import Campaign, Lead
from server.api.services.lead_service import LeadService
from server.utils.logging_config import server_logger

@pytest.fixture
def lead_data():
    """Test lead data."""
    return {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
        'company': 'Test Company',
        'phone': '+1234567890',
        'title': 'Test Title',
        'linkedin_url': 'https://linkedin.com/in/johndoe',
        'source_url': 'https://example.com'
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
    assert response.json['data']['name'] == f"{lead_data['first_name']} {lead_data['last_name']}"
    assert response.json['data']['company_name'] == lead_data['company']

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
        'first_name': 'John',
        'last_name': 'Doe',
        'company': 'Test Company'
    }, headers=auth_headers)
    assert response.status_code == 400
    assert 'Email is required' in response.json['message']

def test_get_lead_success(client, auth_headers, lead_data):
    """Test successful retrieval of a specific lead."""
    # First create a lead
    create_response = client.post('/api/leads', json=lead_data, headers=auth_headers)
    lead_id = create_response.json['data']['id']
    
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
    lead_id = create_response.json['data']['id']
    
    # Then update it
    update_data = {'first_name': 'Updated First Name', 'last_name': 'Updated Last Name', 'status': 'contacted'}
    response = client.put(f'/api/leads/{lead_id}', json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['first_name'] == update_data['first_name']
    assert response.json['data']['last_name'] == update_data['last_name']
    assert response.json['data']['status'] == update_data['status']

def test_update_lead_not_found(client, auth_headers):
    """Test updating a non-existent lead."""
    response = client.put('/api/leads/nonexistent', json={'first_name': 'Updated', 'last_name': 'Updated'}, headers=auth_headers)
    assert response.status_code == 404
    assert response.json['status'] == 'error'
    assert response.json['message'] == 'Lead not found'

def test_delete_lead_success(client, auth_headers, lead_data):
    """Test successful lead deletion."""
    # First create a lead
    create_response = client.post('/api/leads', json=lead_data, headers=auth_headers)
    lead_id = create_response.json['data']['id']
    
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

def test_lead_creation(app, client, db_session, schemas, auth_headers, lead_data):
    """Test lead creation with valid data."""
    with app.app_context():
        # Create test campaign
        campaign = Campaign(
            name='Test Campaign',
            description='Test Description',
            status='created'
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Add campaign_id to lead data
        lead_data['campaign_id'] = campaign.id
        
        # Make request to create lead
        response = client.post('/api/leads', json=lead_data, headers=auth_headers)
        
        # Validate response
        assert response.status_code == 201
        assert response.json['status'] == 'success'
        
        # Validate lead data
        lead = response.json['data']
        assert lead['first_name'] == lead_data['first_name']
        assert lead['last_name'] == lead_data['last_name']
        assert lead['email'] == lead_data['email']
        assert lead['company'] == lead_data['company']
        assert lead['phone'] == lead_data['phone']
        assert lead['title'] == lead_data['title']
        assert lead['linkedin_url'] == lead_data['linkedin_url']
        assert lead['source_url'] == lead_data['source_url']
        assert lead['campaign_id'] == campaign.id
        assert 'id' in lead
        assert 'created_at' in lead
        assert 'updated_at' in lead

def test_lead_with_missing_required_fields(app, client, db_session, schemas, auth_headers):
    """Test lead creation with missing required fields."""
    with app.app_context():
        # Create test campaign
        campaign = Campaign(
            name='Test Campaign',
            description='Test Description',
            status='created'
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Create test lead data with missing email
        lead_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'company': 'Test Company',
            'title': 'Test Title',
            'campaign_id': campaign.id
        }
        
        # Make request to create lead
        response = client.post('/api/leads', json=lead_data, headers=auth_headers)
        
        # Validate error response format
        assert response.status_code == 400
        errors = schemas['error'].validate(response.json)
        assert not errors, f"Error response validation errors: {errors}"
        
        # Verify error message
        assert response.json['error']['message'] == 'Email is required'

def test_lead_with_invalid_email(app, client, db_session, schemas, auth_headers):
    """Test lead creation with invalid email."""
    with app.app_context():
        # Create test campaign
        campaign = Campaign(
            name='Test Campaign',
            description='Test Description',
            status='created'
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Create test lead data with invalid email
        lead_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'invalid-email',
            'company': 'Test Company',
            'title': 'Test Title',
            'campaign_id': campaign.id
        }
        
        # Make request to create lead
        response = client.post('/api/leads', json=lead_data, headers=auth_headers)
        
        # Validate error response format
        assert response.status_code == 400
        errors = schemas['error'].validate(response.json)
        assert not errors, f"Error response validation errors: {errors}"
        
        # Verify error message
        assert response.json['error']['message'] == 'Invalid email format'

def test_lead_duplicate(app, client, db_session, schemas, auth_headers):
    """Test creating a duplicate lead."""
    with app.app_context():
        # Create test campaign
        campaign = Campaign(
            name='Test Campaign',
            description='Test Description',
            status='created'
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Create test lead
        lead = Lead(
            campaign_id=campaign.id,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            company='Test Company',
            title='Test Title'
        )
        db_session.add(lead)
        db_session.commit()
        
        # Create test lead data for duplicate
        lead_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'company': 'New Company',
            'title': 'New Title',
            'campaign_id': campaign.id
        }
        
        # Make request to create duplicate lead
        response = client.post('/api/leads', json=lead_data, headers=auth_headers)
        
        # Validate response format
        assert response.status_code == 200
        errors = schemas['success'].validate(response.json)
        assert not errors, f"Response validation errors: {errors}"
        
        # Validate lead data
        lead_data = response.json['data']
        errors = schemas['lead'].validate(lead_data)
        assert not errors, f"Lead data validation errors: {errors}"
        
        # Verify lead was not duplicated
        leads = Lead.query.filter_by(email='john@example.com').all()
        assert len(leads) == 1

def test_lead_list(app, client, db_session, schemas, auth_headers):
    """Test listing leads for a campaign."""
    with app.app_context():
        # Create test campaign
        campaign = Campaign(
            name='Test Campaign',
            description='Test Description',
            status='created'
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Create test leads
        leads = [
            Lead(
                campaign_id=campaign.id,
                first_name=f'Test',
                last_name=f'Lead {i}',
                email=f'lead{i}@example.com',
                company=f'Company {i}',
                title=f'Title {i}'
            )
            for i in range(3)
        ]
        for lead in leads:
            db_session.add(lead)
        db_session.commit()
        
        # Make request to list leads
        response = client.get('/api/leads', headers=auth_headers)
        
        # Validate response format
        assert response.status_code == 200
        errors = schemas['success'].validate(response.json)
        assert not errors, f"Response validation errors: {errors}"
        
        # Validate lead list data
        lead_list = response.json['data']
        assert len(lead_list) == 3
        for lead_data in lead_list:
            errors = schemas['lead'].validate(lead_data)
            assert not errors, f"Lead data validation errors: {errors}"

def test_lead_not_found(app, client, db_session, schemas, auth_headers):
    """Test accessing a non-existent lead."""
    with app.app_context():
        # Create test campaign
        campaign = Campaign(
            name='Test Campaign',
            description='Test Description',
            status='created'
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Make request to get non-existent lead
        response = client.get('/api/leads/nonexistent', headers=auth_headers)
        
        # Validate error response format
        assert response.status_code == 404
        errors = schemas['error'].validate(response.json)
        assert not errors, f"Error response validation errors: {errors}"
        
        # Verify error message
        assert response.json['error']['message'] == 'Lead not found'

def test_get_lead(app, client, db_session, schemas, auth_headers, lead_data):
    """Test getting a specific lead."""
    with app.app_context():
        # Create test campaign
        campaign = Campaign(
            name='Test Campaign',
            description='Test Description',
            status='created'
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Create test lead
        lead_service = LeadService()
        lead_data['campaign_id'] = campaign.id
        created_lead = lead_service.create_lead(lead_data)
        
        # Make request to get lead
        response = client.get(f'/api/leads/{created_lead["id"]}', headers=auth_headers)
        
        # Validate response
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        
        # Validate lead data
        lead = response.json['data']
        assert lead['id'] == created_lead['id']
        assert lead['first_name'] == lead_data['first_name']
        assert lead['last_name'] == lead_data['last_name']
        assert lead['email'] == lead_data['email']
        assert lead['company'] == lead_data['company']
        assert lead['phone'] == lead_data['phone']
        assert lead['title'] == lead_data['title']
        assert lead['linkedin_url'] == lead_data['linkedin_url']
        assert lead['source_url'] == lead_data['source_url']
        assert lead['campaign_id'] == campaign.id

def test_update_lead(app, client, db_session, schemas, auth_headers, lead_data):
    """Test updating a lead."""
    with app.app_context():
        # Create test campaign
        campaign = Campaign(
            name='Test Campaign',
            description='Test Description',
            status='created'
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Create test lead
        lead_service = LeadService()
        lead_data['campaign_id'] = campaign.id
        created_lead = lead_service.create_lead(lead_data)
        
        # Update lead data
        update_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@example.com',
            'company': 'New Company',
            'phone': '+9876543210',
            'title': 'New Title',
            'linkedin_url': 'https://linkedin.com/in/janesmith',
            'source_url': 'https://newexample.com',
            'campaign_id': campaign.id
        }
        
        # Make request to update lead
        response = client.put(f'/api/leads/{created_lead["id"]}', json=update_data, headers=auth_headers)
        
        # Validate response
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        
        # Validate updated lead data
        lead = response.json['data']
        assert lead['id'] == created_lead['id']
        assert lead['first_name'] == update_data['first_name']
        assert lead['last_name'] == update_data['last_name']
        assert lead['email'] == update_data['email']
        assert lead['company'] == update_data['company']
        assert lead['phone'] == update_data['phone']
        assert lead['title'] == update_data['title']
        assert lead['linkedin_url'] == update_data['linkedin_url']
        assert lead['source_url'] == update_data['source_url']
        assert lead['campaign_id'] == campaign.id

def test_delete_lead(app, client, db_session, schemas, auth_headers, lead_data):
    """Test deleting a lead."""
    with app.app_context():
        # Create test campaign
        campaign = Campaign(
            name='Test Campaign',
            description='Test Description',
            status='created'
        )
        db_session.add(campaign)
        db_session.commit()
        
        # Create test lead
        lead_service = LeadService()
        lead_data['campaign_id'] = campaign.id
        created_lead = lead_service.create_lead(lead_data)
        
        # Make request to delete lead
        response = client.delete(f'/api/leads/{created_lead["id"]}', headers=auth_headers)
        
        # Validate response
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        assert response.json['message'] == 'Lead deleted successfully'
        
        # Verify lead is deleted
        get_response = client.get(f'/api/leads/{created_lead["id"]}', headers=auth_headers)
        assert get_response.status_code == 404

def test_invalid_json_payload(app, client, db_session, schemas, auth_headers):
    """Test handling of invalid JSON payloads."""
    response = client.post('/api/leads',
        data='invalid json',
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code == 400
    assert response.json['status'] == 'error'
    assert response.json['error']['message'] == 'Invalid JSON payload' 