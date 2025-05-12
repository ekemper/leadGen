"""
Tests for API endpoints (health check and root endpoint).
"""
import pytest
from flask import json
from server.app import create_app

@pytest.fixture
def client():
    app = create_app({'TESTING': True})
    with app.test_client() as client:
        yield client

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

def test_webhook_happy_path_ngrok(client):
    """Should accept POST from ngrok (X-Forwarded-For present) and return 200."""
    payload = {"actorId": "test-actor", "eventType": "ACTOR.RUN.SUCCEEDED"}
    headers = {
        'X-Forwarded-For': '3.8.8.8',  # Simulate ngrok
        'Content-Type': 'application/json',
    }
    resp = client.post('/api/apify-webhook', data=json.dumps(payload), headers=headers)
    assert resp.status_code == 200
    assert resp.json['status'] == 'success'

def test_webhook_forbidden_localhost(client):
    """Should reject POST from localhost (no X-Forwarded-For) with 403."""
    payload = {"actorId": "test-actor", "eventType": "ACTOR.RUN.SUCCEEDED"}
    headers = {'Content-Type': 'application/json'}
    resp = client.post('/api/apify-webhook', data=json.dumps(payload), headers=headers)
    assert resp.status_code == 403
    assert resp.json['status'] == 'error'
    assert 'Forbidden' in resp.json['message']

def test_webhook_empty_payload(client):
    """Should accept empty JSON if X-Forwarded-For is present."""
    headers = {'X-Forwarded-For': '1.2.3.4', 'Content-Type': 'application/json'}
    resp = client.post('/api/apify-webhook', data=json.dumps({}), headers=headers)
    assert resp.status_code == 200
    assert resp.json['status'] == 'success'

def test_webhook_malformed_json(client):
    """Should return 400 for malformed JSON, even if X-Forwarded-For is present."""
    headers = {'X-Forwarded-For': '1.2.3.4', 'Content-Type': 'application/json'}
    resp = client.post('/api/apify-webhook', data='{notjson}', headers=headers)
    assert resp.status_code == 400
    assert resp.json['status'] == 'error'

def test_webhook_wrong_method(client):
    """Should return 405 for GET requests (method not allowed)."""
    headers = {'X-Forwarded-For': '1.2.3.4'}
    resp = client.get('/api/apify-webhook', headers=headers)
    assert resp.status_code == 405 