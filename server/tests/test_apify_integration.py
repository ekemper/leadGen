import pytest
from flask import Flask, jsonify
from unittest.mock import patch, MagicMock
from server.app import create_app
from server.models import Campaign, Job, Lead
from server.config.database import db
import json

@pytest.fixture
def client():
    app = create_app({'TESTING': True})
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def default_campaign_data():
    return {
        'name': 'Test Campaign',
        'description': 'Integration test campaign',
        'organization_id': 'org-123',
        'searchUrl': 'https://app.apollo.io/#/people?page=1',
        'count': 10,
        'excludeGuessedEmails': True,
        'excludeNoEmails': False,
        'getEmails': True
    }

def make_webhook_payload(job_id, dataset_id, event_type='ACTOR.RUN.SUCCEEDED', items=None):
    return {
        'job_id': job_id,
        'apify_run_id': 'run-abc',
        'apify_dataset_id': dataset_id,
        'eventType': event_type,
        'eventData': {'actorId': 'actor-xyz', 'actorRunId': 'run-abc'},
        'resource': {'id': 'run-abc', 'defaultDatasetId': dataset_id},
    }

@patch('server.background_services.apollo_service.ApifyClient')
def test_apify_webhook_happy_path(mock_apify_client, client):
    """Happy path: webhook with valid job_id, dataset_id, and eventType."""
    # Setup campaign and job
    campaign = Campaign(id='camp-1', name='Test', description='desc', organization_id='org-123', searchUrl='url', count=10)
    db.session.add(campaign)
    job = Job(id='job-1', campaign_id='camp-1', job_type='FETCH_LEADS', status='PENDING')
    db.session.add(job)
    db.session.commit()
    # Mock Apify dataset fetch
    mock_dataset = MagicMock()
    mock_dataset.list_items.return_value.items = [
        {'first_name': 'Alice', 'last_name': 'Smith', 'email': 'alice@example.com'},
        {'first_name': 'Bob', 'last_name': 'Jones', 'email': 'bob@example.com'}
    ]
    mock_apify_client.return_value.dataset.return_value = mock_dataset
    # Simulate webhook
    payload = make_webhook_payload('job-1', 'ds-1')
    headers = {'X-Forwarded-For': '3.8.8.8', 'Content-Type': 'application/json'}
    resp = client.post('/api/apify-webhook', data=json.dumps(payload), headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    # Check leads saved
    leads = Lead.query.filter_by(campaign_id='camp-1').all()
    assert len(leads) == 2
    assert {l.email for l in leads} == {'alice@example.com', 'bob@example.com'}
    # Check job status
    job = Job.query.get('job-1')
    assert job.status == 'COMPLETED'
    assert job.result['total_count'] == 2

@patch('server.background_services.apollo_service.ApifyClient')
def test_apify_webhook_missing_job_id(mock_apify_client, client):
    """Edge: missing job_id in payload."""
    payload = make_webhook_payload(None, 'ds-1')
    headers = {'X-Forwarded-For': '3.8.8.8', 'Content-Type': 'application/json'}
    resp = client.post('/api/apify-webhook', data=json.dumps(payload), headers=headers)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['status'] == 'error'
    assert 'Job not found' in data['message']

@patch('server.background_services.apollo_service.ApifyClient')
def test_apify_webhook_invalid_dataset_id(mock_apify_client, client):
    """Edge: invalid dataset_id triggers Apify fetch error."""
    campaign = Campaign(id='camp-2', name='Test', description='desc', organization_id='org-123', searchUrl='url', count=10)
    db.session.add(campaign)
    job = Job(id='job-2', campaign_id='camp-2', job_type='FETCH_LEADS', status='PENDING')
    db.session.add(job)
    db.session.commit()
    mock_apify_client.return_value.dataset.side_effect = Exception('Dataset not found')
    payload = make_webhook_payload('job-2', 'bad-ds')
    headers = {'X-Forwarded-For': '3.8.8.8', 'Content-Type': 'application/json'}
    resp = client.post('/api/apify-webhook', data=json.dumps(payload), headers=headers)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['status'] == 'error'
    assert 'Error fetching dataset' in data['message']

@patch('server.background_services.apollo_service.ApifyClient')
def test_apify_webhook_wrong_event_type(mock_apify_client, client):
    """Edge: eventType not ACTOR.RUN.SUCCEEDED is ignored."""
    campaign = Campaign(id='camp-3', name='Test', description='desc', organization_id='org-123', searchUrl='url', count=10)
    db.session.add(campaign)
    job = Job(id='job-3', campaign_id='camp-3', job_type='FETCH_LEADS', status='PENDING')
    db.session.add(job)
    db.session.commit()
    payload = make_webhook_payload('job-3', 'ds-3', event_type='ACTOR.RUN.FAILED')
    headers = {'X-Forwarded-For': '3.8.8.8', 'Content-Type': 'application/json'}
    resp = client.post('/api/apify-webhook', data=json.dumps(payload), headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ignored'
    assert 'eventType' in data['reason']

@patch('server.background_services.apollo_service.ApifyClient')
def test_apify_webhook_malformed_payload(mock_apify_client, client):
    """Edge: malformed JSON returns 400."""
    headers = {'X-Forwarded-For': '3.8.8.8', 'Content-Type': 'application/json'}
    resp = client.post('/api/apify-webhook', data='not a json', headers=headers)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['status'] == 'error'
    assert 'Malformed JSON' in data['message'] 