"""
Tests for campaign endpoints.
"""
import pytest
from flask import json
from server.models import Campaign, Job
from server.models.campaign_status import CampaignStatus
from server.config.database import db
from datetime import datetime, timedelta
import re
from server.models.campaign import Campaign
from server.models.job import Job
from server.models.lead import Lead
from server.api.services.campaign_service import CampaignService
from server.api.services.job_service import JobService
from server.api.services.lead_service import LeadService
from server.utils.logging_config import server_logger

@pytest.fixture
def campaign_data():
    """Test campaign data."""
    return {
        'name': 'Test Campaign',
        'description': 'Test campaign description'
    }

@pytest.fixture
def campaign_start_params():
    """Test campaign start parameters."""
    return {
        'count': 10,
        'excludeGuessedEmails': True,
        'excludeNoEmails': False,
        'getEmails': True,
        'searchUrl': 'https://app.apollo.io/search'
    }

@pytest.fixture
def test_job(client, auth_headers, campaign_data):
    """Create a test job for a campaign."""
    # Create a campaign first
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Create a test job
    with client.application.app_context():
        job = Job(
            id='test-job-id',
            campaign_id=campaign_id,
            job_type='fetch_leads',
            status='completed',
            result={'leads': ['lead1', 'lead2']},
            created_at=datetime.utcnow() - timedelta(days=8)  # 8 days old
        )
        db.session.add(job)
        db.session.commit()
        
        # Store the campaign_id for later use
        job.stored_campaign_id = campaign_id
        
        # Refresh the job to ensure it's properly loaded
        db.session.refresh(job)
    
    return job

def test_create_campaign_success(client, auth_headers, campaign_data):
    """Test successful campaign creation."""
    response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json
    assert data['status'] == 'success'
    assert data['data']['name'] == campaign_data['name']
    assert data['data']['status'] == CampaignStatus.CREATED

def test_get_campaigns(client, auth_headers, campaign_data):
    """Test getting all campaigns."""
    # Create a campaign first
    client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    
    # Get all campaigns
    response = client.get('/api/campaigns', headers=auth_headers)
    assert response.status_code == 200
    data = response.json
    assert data['status'] == 'success'
    assert isinstance(data['data'], list)
    assert len(data['data']) > 0
    assert data['data'][0]['name'] == campaign_data['name']

def test_get_campaign(client, auth_headers, campaign_data):
    """Test getting a single campaign."""
    # Create a campaign first
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Get the campaign
    response = client.get(f'/api/campaigns/{campaign_id}', headers=auth_headers)
    assert response.status_code == 200
    data = response.json
    assert data['status'] == 'success'
    assert data['data']['id'] == campaign_id
    assert data['data']['name'] == campaign_data['name']

def test_start_campaign_success(client, auth_headers, campaign_data, campaign_start_params):
    """Test successful campaign start."""
    # Create a campaign first
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Start the campaign
    response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
    assert response.status_code == 200
    data = response.json
    assert data['status'] == 'success'
    assert data['data']['status'] == CampaignStatus.FETCHING_LEADS

def test_create_and_start_campaign(client, auth_headers, campaign_data, campaign_start_params):
    """Test creating and starting a campaign in one request."""
    # Combine campaign data and start parameters
    params = {**campaign_data, **campaign_start_params}
    
    response = client.post('/api/campaigns/start', json=params, headers=auth_headers)
    assert response.status_code == 201
    data = response.json
    assert data['status'] == 'success'
    assert data['data']['name'] == campaign_data['name']
    assert data['data']['status'] == CampaignStatus.FETCHING_LEADS

def test_create_campaign_missing_name(client, auth_headers):
    """Test campaign creation with missing name."""
    response = client.post('/api/campaigns', json={'description': 'Test description'}, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'name' in data['message'].lower()

def test_get_nonexistent_campaign(client, auth_headers):
    """Test getting a campaign that doesn't exist."""
    response = client.get('/api/campaigns/999999', headers=auth_headers)
    assert response.status_code == 404
    data = response.json
    assert data['status'] == 'error'
    assert 'not found' in data['message'].lower()

def test_start_campaign_missing_params(client, auth_headers, campaign_data):
    """Test starting a campaign with missing parameters."""
    # Create a campaign first
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Try to start without required parameters
    response = client.post(f'/api/campaigns/{campaign_id}/start', json={}, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'no parameters provided' in data['message'].lower()

def test_campaign_status_transitions(client, auth_headers, campaign_data, campaign_start_params):
    """Test campaign status transitions through the workflow."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Verify initial status
    assert create_response.json['data']['status'] == CampaignStatus.CREATED
    
    # Start the campaign
    start_response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
    assert start_response.status_code == 200
    assert start_response.json['data']['status'] == CampaignStatus.FETCHING_LEADS
    
    # Get campaign to verify status
    get_response = client.get(f'/api/campaigns/{campaign_id}', headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json['data']['status'] == CampaignStatus.FETCHING_LEADS

def test_get_campaign_results(client, auth_headers, test_job):
    """Test getting campaign results."""
    campaign_id = test_job.stored_campaign_id
    
    response = client.get(f'/api/campaigns/{campaign_id}/results', headers=auth_headers)
    assert response.status_code == 200
    data = response.json
    assert data['status'] == 'success'
    assert 'leads' in data['data']
    assert len(data['data']['leads']) == 2  # From test_job fixture

def test_start_campaign_invalid_count(client, auth_headers, campaign_data):
    """Test starting a campaign with invalid count parameter."""
    # Create a campaign first
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Try to start with invalid count
    invalid_params = {
        'count': 0,  # Invalid: must be > 0
        'excludeGuessedEmails': True,
        'excludeNoEmails': False,
        'getEmails': True,
        'searchUrl': 'https://app.apollo.io/search'
    }
    
    response = client.post(f'/api/campaigns/{campaign_id}/start', json=invalid_params, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'count must be a positive integer' in data['message'].lower()

def test_start_campaign_invalid_url(client, auth_headers, campaign_data):
    """Test starting a campaign with invalid Apollo URL."""
    # Create a campaign first
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Try to start with invalid URL
    invalid_params = {
        'count': 10,
        'excludeGuessedEmails': True,
        'excludeNoEmails': False,
        'getEmails': True,
        'searchUrl': 'https://invalid-url.com/search'  # Invalid: must be Apollo URL
    }
    
    response = client.post(f'/api/campaigns/{campaign_id}/start', json=invalid_params, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'invalid apollo.io search url' in data['message'].lower()

def test_start_nonexistent_campaign(client, auth_headers, campaign_start_params):
    """Test starting a campaign that doesn't exist."""
    response = client.post('/api/campaigns/999999/start', json=campaign_start_params, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'not found' in data['message'].lower()

def test_get_campaign_results_with_no_jobs(client, auth_headers, campaign_data):
    """Test getting results for a campaign with no jobs."""
    # Create a campaign first
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Try to get results
    response = client.get(f'/api/campaigns/{campaign_id}/results', headers=auth_headers)
    assert response.status_code == 404
    data = response.json
    assert data['status'] == 'error'
    assert 'no completed job found for this campaign' in data['message'].lower()

def test_start_campaign_with_invalid_status(client, auth_headers, campaign_data, campaign_start_params):
    """Test starting a campaign that's already in progress."""
    # Create and start a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
    
    # Try to start it again
    response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'campaign is already being started' in data['message'].lower()

def test_create_campaign_with_sql_injection(client, auth_headers):
    """Test campaign creation with SQL injection attempt."""
    malicious_data = {
        'name': "Test Campaign'; DROP TABLE campaigns; --",
        'description': 'Malicious description'
    }
    response = client.post('/api/campaigns', json=malicious_data, headers=auth_headers)
    assert response.status_code == 201  # Should still create successfully
    data = response.json
    assert data['status'] == 'success'
    # Verify the name was stored as is (SQLAlchemy handles escaping)
    assert data['data']['name'] == malicious_data['name']

def test_create_campaign_with_xss_attempt(client, auth_headers):
    """Test campaign creation with XSS attempt."""
    xss_data = {
        'name': '<script>alert("XSS")</script>Test Campaign',
        'description': '<img src="x" onerror="alert(\'XSS\')">'
    }
    response = client.post('/api/campaigns', json=xss_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json
    assert data['status'] == 'success'
    # Verify the data was stored as is (frontend should handle escaping)
    assert data['data']['name'] == xss_data['name']
    assert data['data']['description'] == xss_data['description']

def test_create_campaign_with_special_characters(client, auth_headers):
    """Test campaign creation with special characters."""
    special_chars_data = {
        'name': '!@#$%^&*()_+-=[]{}|;:,.<>?/~`"\'\\',
        'description': 'Test description with émojis 🎉🚀'
    }
    response = client.post('/api/campaigns', json=special_chars_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json
    assert data['status'] == 'success'
    assert data['data']['name'] == special_chars_data['name']
    assert data['data']['description'] == special_chars_data['description']

def test_create_campaign_with_very_long_description(client, auth_headers):
    """Test campaign creation with a very long description."""
    long_description = 'x' * 10000  # 10,000 characters
    response = client.post('/api/campaigns', json={
        'name': 'Test Campaign',
        'description': long_description
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json
    assert data['status'] == 'success'
    assert len(data['data']['description']) == len(long_description)

def test_start_campaign_with_invalid_count_range(client, auth_headers, campaign_data):
    """Test starting a campaign with count outside valid range."""
    # Create a campaign first
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Try with too large count
    invalid_params = {
        'count': 1000000,  # Unreasonably large
        'excludeGuessedEmails': True,
        'excludeNoEmails': False,
        'getEmails': True,
        'searchUrl': 'https://app.apollo.io/search'
    }
    
    response = client.post(f'/api/campaigns/{campaign_id}/start', json=invalid_params, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'count' in data['message'].lower()

def test_start_campaign_with_malicious_url(client, auth_headers, campaign_data):
    """Test starting a campaign with potentially malicious URL."""
    # Create a campaign first
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Try with malicious URL
    invalid_params = {
        'count': 10,
        'excludeGuessedEmails': True,
        'excludeNoEmails': False,
        'getEmails': True,
        'searchUrl': 'https://app.apollo.io.malicious.com/search'  # Malicious domain
    }
    
    response = client.post(f'/api/campaigns/{campaign_id}/start', json=invalid_params, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'invalid apollo.io search url' in data['message'].lower()

def test_concurrent_campaign_start(client, auth_headers, campaign_data, campaign_start_params):
    """Test starting a campaign concurrently from multiple requests."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Try to start the campaign twice simultaneously
    import threading
    results = []
    
    def start_campaign():
        response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
        results.append(response)
    
    # Create two threads to start the campaign
    thread1 = threading.Thread(target=start_campaign)
    thread2 = threading.Thread(target=start_campaign)
    
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    
    # One should succeed, one should fail
    success_count = sum(1 for r in results if r.status_code == 200)
    error_count = sum(1 for r in results if r.status_code == 400)
    assert success_count == 1
    assert error_count == 1

def test_campaign_status_race_condition(client, auth_headers, campaign_data):
    """Test handling of race conditions in campaign status updates."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Get initial status
    initial_response = client.get(f'/api/campaigns/{campaign_id}', headers=auth_headers)
    initial_status = initial_response.json['data']['status']
    
    # Simulate concurrent status updates
    import threading
    results = []
    
    def update_status():
        response = client.get(f'/api/campaigns/{campaign_id}', headers=auth_headers)
        results.append(response.json['data']['status'])
    
    # Create multiple threads to read status
    threads = [threading.Thread(target=update_status) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # All statuses should be consistent
    assert all(status == initial_status for status in results)

def test_concurrent_job_cleanup(client, auth_headers, test_job):
    """Test concurrent cleanup of campaign jobs."""
    campaign_id = test_job.stored_campaign_id
    
    # Simulate concurrent cleanup requests
    import threading
    results = []
    
    def cleanup_jobs():
        response = client.post(f'/api/campaigns/{campaign_id}/cleanup', json={'days': 7}, headers=auth_headers)
        results.append(response)
    
    # Create multiple threads to cleanup jobs
    threads = [threading.Thread(target=cleanup_jobs) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # All requests should succeed
    assert all(r.status_code == 200 for r in results)

def test_campaign_recovery_after_failure(client, auth_headers, campaign_data, campaign_start_params):
    """Test campaign recovery after a failure."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Simulate a failure by creating a failed job
    with client.application.app_context():
        failed_job = Job(
            id='failed-job-id',
            campaign_id=campaign_id,
            job_type='fetch_leads',
            status='failed',
            error='Test failure',
            created_at=datetime.utcnow()
        )
        db.session.add(failed_job)
        db.session.commit()
    
    # Try to start the campaign again
    response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
    assert response.status_code == 200
    data = response.json
    assert data['status'] == 'success'
    assert data['data']['status'] == 'fetching_leads'

def test_campaign_with_invalid_job_data(client, auth_headers, campaign_data):
    """Test handling of campaigns with invalid job data."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Create a job with invalid data
    with client.application.app_context():
        invalid_job = Job(
            id='invalid-job-id',
            campaign_id=campaign_id,
            job_type='invalid_type',  # Invalid job type
            status='completed',
            result={'invalid': 'data'},
            created_at=datetime.utcnow()
        )
        db.session.add(invalid_job)
        db.session.commit()
    
    # Try to get campaign results
    response = client.get(f'/api/campaigns/{campaign_id}/results', headers=auth_headers)
    assert response.status_code == 404
    data = response.json
    assert data['status'] == 'error'
    assert 'invalid job type' in data['message'].lower()

def test_campaign_with_missing_required_fields(client, auth_headers):
    """Test campaign creation with missing required fields."""
    # Try to create campaign with empty data
    response = client.post('/api/campaigns', json={}, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'no data provided' in data['message'].lower()
    
    # Try to create campaign with only description
    response = client.post('/api/campaigns', json={'description': 'Test'}, headers=auth_headers)
    assert response.status_code == 400
    data = response.json
    assert data['status'] == 'error'
    assert 'name' in data['message'].lower()

def test_campaign_with_invalid_status_transition(client, auth_headers, campaign_data):
    """Test handling of invalid campaign status transitions."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Try to update status directly (should fail)
    with client.application.app_context():
        campaign = Campaign.query.get(campaign_id)
        try:
            campaign.update_status('invalid_status')
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert 'invalid status' in str(e).lower()

def test_campaign_with_corrupted_job_data(client, auth_headers, campaign_data):
    """Test handling of campaigns with corrupted job data."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Create a job with corrupted data
    with client.application.app_context():
        corrupted_job = Job(
            id='corrupted-job-id',
            campaign_id=campaign_id,
            job_type='fetch_leads',
            status='completed',
            result=None,  # Corrupted result
            created_at=datetime.utcnow()
        )
        db.session.add(corrupted_job)
        db.session.commit()
    
    # Try to get campaign results
    response = client.get(f'/api/campaigns/{campaign_id}/results', headers=auth_headers)
    assert response.status_code == 404
    data = response.json
    assert data['status'] == 'error'
    assert 'job result data is corrupted' in data['message'].lower()

def test_campaign_status_transition_complete_workflow(client, auth_headers, campaign_data, campaign_start_params):
    """Test complete campaign lifecycle status transitions."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Test CREATED -> FETCHING_LEADS -> COMPLETED
    start_response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
    assert start_response.status_code == 200
    assert start_response.json['data']['status'] == CampaignStatus.FETCHING_LEADS
    
    # Simulate job completion
    with client.application.app_context():
        job = Job(
            id='completed-job-id',
            campaign_id=campaign_id,
            job_type='fetch_leads',
            status='completed',
            result={'leads': ['lead1', 'lead2']},
            created_at=datetime.utcnow()
        )
        db.session.add(job)
        db.session.commit()
    
    # Verify campaign status is updated
    get_response = client.get(f'/api/campaigns/{campaign_id}', headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json['data']['status'] == CampaignStatus.COMPLETED

def test_campaign_status_transition_with_failure(client, auth_headers, campaign_data, campaign_start_params):
    """Test campaign status transitions with failure and retry."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Start campaign
    start_response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
    assert start_response.status_code == 200
    assert start_response.json['data']['status'] == CampaignStatus.FETCHING_LEADS
    
    # Simulate job failure
    with client.application.app_context():
        failed_job = Job(
            id='failed-job-id',
            campaign_id=campaign_id,
            job_type='fetch_leads',
            status='failed',
            error='Test failure',
            created_at=datetime.utcnow()
        )
        db.session.add(failed_job)
        db.session.commit()
    
    # Verify campaign status is updated to failed
    get_response = client.get(f'/api/campaigns/{campaign_id}', headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json['data']['status'] == CampaignStatus.FAILED
    
    # Retry the campaign
    retry_response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
    assert retry_response.status_code == 200
    assert retry_response.json['data']['status'] == CampaignStatus.FETCHING_LEADS

def test_campaign_job_result_validation(client, auth_headers, campaign_data):
    """Test various job result validation scenarios."""
    # Create a campaign
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Test malformed JSON result
    with client.application.app_context():
        malformed_job = Job(
            id='malformed-job-id',
            campaign_id=campaign_id,
            job_type='fetch_leads',
            status='completed',
            result='{"invalid": json}',  # Malformed JSON
            created_at=datetime.utcnow()
        )
        db.session.add(malformed_job)
        db.session.commit()
    
    response = client.get(f'/api/campaigns/{campaign_id}/results', headers=auth_headers)
    assert response.status_code == 404
    assert 'job result must be a dictionary' in response.json['message'].lower()
    
    # Test missing required fields
    with client.application.app_context():
        incomplete_job = Job(
            id='incomplete-job-id',
            campaign_id=campaign_id,
            job_type='fetch_leads',
            status='completed',
            result={'some_field': 'value'},  # Missing required 'leads' field
            created_at=datetime.utcnow()
        )
        db.session.add(incomplete_job)
        db.session.commit()
    
    response = client.get(f'/api/campaigns/{campaign_id}/results', headers=auth_headers)
    assert response.status_code == 404
    assert 'job result data is corrupted' in response.json['message'].lower()
    
    # Test empty results
    with client.application.app_context():
        empty_job = Job(
            id='empty-job-id',
            campaign_id=campaign_id,
            job_type='fetch_leads',
            status='completed',
            result={'leads': []},  # Empty leads list
            created_at=datetime.utcnow()
        )
        db.session.add(empty_job)
        db.session.commit()
    
    response = client.get(f'/api/campaigns/{campaign_id}/results', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['data']['leads'] == []

def test_campaign_resource_cleanup(client, auth_headers, test_job):
    """Test proper cleanup of campaign resources."""
    campaign_id = test_job.stored_campaign_id
    
    # Create multiple jobs for the campaign
    with client.application.app_context():
        for i in range(5):
            job = Job(
                id=f'old-job-{i}',
                campaign_id=campaign_id,
                job_type='fetch_leads',
                status='completed',
                result={'leads': ['lead1']},
                created_at=datetime.utcnow() - timedelta(days=10)  # 10 days old
            )
            db.session.add(job)
        db.session.commit()
    
    # Clean up jobs older than 7 days
    cleanup_response = client.post(f'/api/campaigns/{campaign_id}/cleanup', json={'days': 7}, headers=auth_headers)
    assert cleanup_response.status_code == 200
    assert 'Successfully cleaned up 5 old jobs' in cleanup_response.json['message']
    
    # Verify jobs are actually deleted
    with client.application.app_context():
        remaining_jobs = Job.query.filter_by(campaign_id=campaign_id).count()
        assert remaining_jobs == 1  # Only the test_job should remain

def test_campaign_performance(client, auth_headers, campaign_data):
    """Test campaign performance under load."""
    import time
    
    # Test response time for campaign creation
    start_time = time.time()
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    creation_time = time.time() - start_time
    assert creation_time < 1.0  # Should complete within 1 second
    
    campaign_id = create_response.json['data']['id']
    
    # Test response time for campaign retrieval
    start_time = time.time()
    get_response = client.get(f'/api/campaigns/{campaign_id}', headers=auth_headers)
    retrieval_time = time.time() - start_time
    assert retrieval_time < 0.5  # Should complete within 0.5 seconds
    
    # Test concurrent campaign creation
    import threading
    results = []
    errors = []
    
    def create_campaign():
        try:
            response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
            results.append(response)
        except Exception as e:
            errors.append(e)
    
    # Create 10 campaigns concurrently
    threads = [threading.Thread(target=create_campaign) for _ in range(10)]
    start_time = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    concurrent_time = time.time() - start_time
    
    assert concurrent_time < 5.0  # Should complete within 5 seconds
    assert len(errors) == 0  # No errors should occur
    assert len(results) == 10  # All campaigns should be created

def test_campaign_error_handling(client, auth_headers, campaign_data, campaign_start_params):
    """Test comprehensive error handling."""
    # Test network failure simulation
    with client.application.app_context():
        # Simulate database connection issue
        db.session.close()
        response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
        assert response.status_code == 500
        assert 'Failed to create campaign' in response.json['message']
    
    # Test invalid state transition
    create_response = client.post('/api/campaigns', json=campaign_data, headers=auth_headers)
    campaign_id = create_response.json['data']['id']
    
    # Try to start a completed campaign
    with client.application.app_context():
        campaign = Campaign.query.get(campaign_id)
        campaign.status = CampaignStatus.COMPLETED
        db.session.commit()
    
    response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
    assert response.status_code == 400
    assert 'cannot start campaign' in response.json['message'].lower()
    
    # Test concurrent error scenarios
    import threading
    results = []
    
    def start_campaign():
        response = client.post(f'/api/campaigns/{campaign_id}/start', json=campaign_start_params, headers=auth_headers)
        results.append(response)
    
    # Try to start the same campaign multiple times
    threads = [threading.Thread(target=start_campaign) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Verify only one request succeeded
    success_count = sum(1 for r in results if r.status_code == 200)
    error_count = sum(1 for r in results if r.status_code == 400)
    assert success_count == 1
    assert error_count == 2

def test_campaign_creation(test_app, test_client, test_db, schemas):
    """Test campaign creation with valid data."""
    # Create test campaign data
    campaign_data = {
        'name': 'Test Campaign',
        'description': 'Test Description'
    }
    
    # Make request to create campaign
    response = test_client.post('/api/campaigns', json=campaign_data)
    
    # Validate response format
    assert response.status_code == 201
    errors = schemas['success'].validate(response.json)
    assert not errors, f"Response validation errors: {errors}"
    
    # Validate campaign data
    campaign_data = response.json['data']
    errors = schemas['campaign'].validate(campaign_data)
    assert not errors, f"Campaign data validation errors: {errors}"
    
    # Verify campaign was created in database
    campaign = Campaign.query.filter_by(name='Test Campaign').first()
    assert campaign is not None
    assert campaign.name == 'Test Campaign'
    assert campaign.description == 'Test Description'
    assert campaign.status == 'created'

def test_campaign_with_missing_required_fields(test_app, test_client, test_db, schemas):
    """Test campaign creation with missing required fields."""
    # Create test campaign data with missing name
    campaign_data = {
        'description': 'Test Description'
    }
    
    # Make request to create campaign
    response = test_client.post('/api/campaigns', json=campaign_data)
    
    # Validate error response format
    assert response.status_code == 400
    errors = schemas['error'].validate(response.json)
    assert not errors, f"Error response validation errors: {errors}"
    
    # Verify error message
    assert response.json['error']['message'] == 'Missing required field: name'

def test_campaign_with_invalid_data(test_app, test_client, test_db, schemas):
    """Test campaign creation with invalid data."""
    # Create test campaign data with invalid name (empty string)
    campaign_data = {
        'name': '',
        'description': 'Test Description'
    }
    
    # Make request to create campaign
    response = test_client.post('/api/campaigns', json=campaign_data)
    
    # Validate error response format
    assert response.status_code == 400
    errors = schemas['error'].validate(response.json)
    assert not errors, f"Error response validation errors: {errors}"
    
    # Verify error message
    assert response.json['error']['message'] == 'Name cannot be empty'

def test_campaign_start(test_app, test_client, test_db, schemas):
    """Test starting a campaign."""
    # Create test campaign
    campaign = Campaign(
        name='Test Campaign',
        description='Test Description',
        status='created'
    )
    test_db.session.add(campaign)
    test_db.session.commit()
    
    # Create test start data
    start_data = {
        'searchUrl': 'https://example.com',
        'count': 10,
        'excludeGuessedEmails': True,
        'excludeNoEmails': True,
        'getEmails': True
    }
    
    # Make request to start campaign
    response = test_client.post(f'/api/campaigns/{campaign.id}/start', json=start_data)
    
    # Validate response format
    assert response.status_code == 200
    errors = schemas['success'].validate(response.json)
    assert not errors, f"Response validation errors: {errors}"
    
    # Validate job data
    job_data = response.json['data']
    errors = schemas['job'].validate(job_data)
    assert not errors, f"Job data validation errors: {errors}"
    
    # Verify campaign status was updated
    campaign = Campaign.query.get(campaign.id)
    assert campaign.status == 'running'
    assert campaign.status_message == 'Campaign started successfully'

def test_campaign_start_with_invalid_data(test_app, test_client, test_db, schemas):
    """Test starting a campaign with invalid data."""
    # Create test campaign
    campaign = Campaign(
        name='Test Campaign',
        description='Test Description',
        status='created'
    )
    test_db.session.add(campaign)
    test_db.session.commit()
    
    # Create test start data with invalid count
    start_data = {
        'searchUrl': 'https://example.com',
        'count': 0,  # Invalid count
        'excludeGuessedEmails': True,
        'excludeNoEmails': True,
        'getEmails': True
    }
    
    # Make request to start campaign
    response = test_client.post(f'/api/campaigns/{campaign.id}/start', json=start_data)
    
    # Validate error response format
    assert response.status_code == 400
    errors = schemas['error'].validate(response.json)
    assert not errors, f"Error response validation errors: {errors}"
    
    # Verify error message
    assert response.json['error']['message'] == 'Count must be between 1 and 100'

def test_campaign_not_found(test_app, test_client, test_db, schemas):
    """Test accessing a non-existent campaign."""
    # Make request to get non-existent campaign
    response = test_client.get('/api/campaigns/non-existent-id')
    
    # Validate error response format
    assert response.status_code == 404
    errors = schemas['error'].validate(response.json)
    assert not errors, f"Error response validation errors: {errors}"
    
    # Verify error message
    assert response.json['error']['message'] == 'Campaign not found'

def test_campaign_list(test_app, test_client, test_db, schemas):
    """Test listing campaigns."""
    # Create test campaigns
    campaigns = [
        Campaign(name=f'Test Campaign {i}', description=f'Test Description {i}')
        for i in range(3)
    ]
    for campaign in campaigns:
        test_db.session.add(campaign)
    test_db.session.commit()
    
    # Make request to list campaigns
    response = test_client.get('/api/campaigns')
    
    # Validate response format
    assert response.status_code == 200
    errors = schemas['success'].validate(response.json)
    assert not errors, f"Response validation errors: {errors}"
    
    # Validate campaign list data
    campaign_list = response.json['data']
    assert len(campaign_list) == 3
    for campaign_data in campaign_list:
        errors = schemas['campaign'].validate(campaign_data)
        assert not errors, f"Campaign data validation errors: {errors}"

# End of test file 