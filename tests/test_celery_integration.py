import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.workers.tasks import health_check

def test_celery_health_check(client):
    """Test that Celery is configured correctly"""
    # This test requires a running Celery worker
    # For unit tests, we'll just check the task can be called directly
    result = health_check()
    assert result["status"] == "healthy"
    assert "timestamp" in result

def test_create_job_endpoint(authenticated_client, existing_campaign):
    """Test job creation endpoint integration."""
    # Create a campaign first 
    campaign_payload = {
        "name": "Test Campaign for Jobs",
        "description": "Campaign for job tests",
        "organization_id": existing_campaign.organization_id,
        "fileName": "job_test.csv",
        "totalRecords": 10,
        "url": "https://app.apollo.io/#/job-test"
    }
    campaign_response = authenticated_client.post("/api/v1/campaigns/", json=campaign_payload)
    assert campaign_response.status_code == 201
    campaign_response_data = campaign_response.json()
    assert "status" in campaign_response_data
    assert "data" in campaign_response_data
    assert campaign_response_data["status"] == "success"
    campaign_data = campaign_response_data["data"]

    # Create a job for the campaign
    job_payload = {
        "name": "Test Job",
        "job_type": "FETCH_LEADS",
        "campaign_id": campaign_data["id"]
    }
    
    response = authenticated_client.post("/api/v1/jobs/", json=job_payload)
    assert response.status_code == 201
    
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    job_data = response_data["data"]
    assert job_data["name"] == "Test Job"
    assert job_data["job_type"] == "FETCH_LEADS"
    assert job_data["campaign_id"] == campaign_data["id"]
    assert "id" in job_data

def test_job_status_endpoint(authenticated_client, existing_campaign):
    """Test job status retrieval."""
    # Create a campaign first
    campaign_payload = {
        "name": "Test Campaign for Job Status",
        "description": "Campaign for job status tests",
        "organization_id": existing_campaign.organization_id,
        "fileName": "job_status_test.csv",
        "totalRecords": 5,
        "url": "https://app.apollo.io/#/job-status-test"
    }
    campaign_response = authenticated_client.post("/api/v1/campaigns/", json=campaign_payload)
    assert campaign_response.status_code == 201
    campaign_response_data = campaign_response.json()
    assert "status" in campaign_response_data
    assert "data" in campaign_response_data
    assert campaign_response_data["status"] == "success"
    campaign_data = campaign_response_data["data"]

    # Create a job
    job_payload = {
        "name": "Status Test Job",
        "job_type": "FETCH_LEADS",
        "campaign_id": campaign_data["id"]
    }
    
    job_response = authenticated_client.post("/api/v1/jobs/", json=job_payload)
    assert job_response.status_code == 201
    job_response_data = job_response.json()
    assert "status" in job_response_data
    assert "data" in job_response_data
    assert job_response_data["status"] == "success"
    job_data = job_response_data["data"]
    
    # Check job status
    status_response = authenticated_client.get(f"/api/v1/jobs/{job_data['id']}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert "status" in status_data
    assert "data" in status_data
    assert status_data["status"] == "success"
    
    job_status = status_data["data"]
    assert job_status["id"] == job_data["id"]
    assert job_status["status"] == "PENDING"  # Jobs are created with PENDING status by default

def test_list_jobs_endpoint(authenticated_client, existing_campaign):
    """Test jobs listing endpoint."""
    # Create a campaign first
    campaign_payload = {
        "name": "Test Campaign for Job List",
        "description": "Campaign for job list tests",
        "organization_id": existing_campaign.organization_id,
        "fileName": "job_list_test.csv",
        "totalRecords": 8,
        "url": "https://app.apollo.io/#/job-list-test"
    }
    campaign_response = authenticated_client.post("/api/v1/campaigns/", json=campaign_payload)
    assert campaign_response.status_code == 201
    campaign_response_data = campaign_response.json()
    assert "status" in campaign_response_data
    assert "data" in campaign_response_data
    assert campaign_response_data["status"] == "success"
    campaign_data = campaign_response_data["data"]

    # Create multiple jobs
    for i in range(3):
        job_payload = {
            "name": f"List Test Job {i}",
            "job_type": "FETCH_LEADS",
            "campaign_id": campaign_data["id"]
        }
        job_response = authenticated_client.post("/api/v1/jobs/", json=job_payload)
        assert job_response.status_code == 201
    
    # List jobs
    response = authenticated_client.get("/api/v1/jobs/")
    assert response.status_code == 200
    
    response_data = response.json()
    assert "status" in response_data
    assert "data" in response_data
    assert response_data["status"] == "success"
    
    jobs_data = response_data["data"]
    assert "jobs" in jobs_data
    assert len(jobs_data["jobs"]) >= 3  # May have jobs from other tests

def test_cancel_job_endpoint(authenticated_client, existing_campaign):
    """Test job cancellation."""
    # Create a campaign first
    campaign_payload = {
        "name": "Test Campaign for Job Cancel",
        "description": "Campaign for job cancel tests",
        "organization_id": existing_campaign.organization_id,
        "fileName": "job_cancel_test.csv",
        "totalRecords": 12,
        "url": "https://app.apollo.io/#/job-cancel-test"
    }
    campaign_response = authenticated_client.post("/api/v1/campaigns/", json=campaign_payload)
    assert campaign_response.status_code == 201
    campaign_response_data = campaign_response.json()
    assert "status" in campaign_response_data
    assert "data" in campaign_response_data
    assert campaign_response_data["status"] == "success"
    campaign_data = campaign_response_data["data"]

    # Create a job to cancel
    job_payload = {
        "name": "Cancel Test Job",
        "job_type": "FETCH_LEADS",
        "campaign_id": campaign_data["id"]
    }
    
    job_response = authenticated_client.post("/api/v1/jobs/", json=job_payload)
    assert job_response.status_code == 201
    job_response_data = job_response.json()
    assert "status" in job_response_data
    assert "data" in job_response_data
    assert job_response_data["status"] == "success"
    job_data = job_response_data["data"]
    
    # Cancel the job
    cancel_response = authenticated_client.post(f"/api/v1/jobs/{job_data['id']}/cancel")
    assert cancel_response.status_code == 200
    
    cancel_data = cancel_response.json()
    assert "status" in cancel_data
    assert "message" in cancel_data or "data" in cancel_data
    
    # Job should be cancelled
    status_response = authenticated_client.get(f"/api/v1/jobs/{job_data['id']}/status")
    assert status_response.status_code == 200
    status_response_data = status_response.json()
    assert "status" in status_response_data
    assert "data" in status_response_data
    assert status_response_data["status"] == "success"
    
    job_status = status_response_data["data"]
    assert job_status["status"] in ["CANCELLED"]   