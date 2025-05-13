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
        'fileName': 'test_file',
        'totalRecords': 10,
        'url': 'https://app.apollo.io/#/people?page=1'
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

# All tests for /api/apify-webhook endpoint removed 