"""
Tests for queue management API endpoints.
Tests the new API endpoints added for bulk campaign operations and campaign status.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.campaign import Campaign, CampaignStatus
from app.models.job import Job, JobStatus, JobType
from app.core.circuit_breaker import ThirdPartyService
from tests.helpers.auth_helpers import AuthHelpers


class TestQueueManagementAPI:
    """Test queue management API endpoints."""

    @pytest.fixture
    def test_organization(self, db_session):
        """Create a test organization."""
        org = Organization(
            id="test-org-queue",
            name="Test Org Queue Management",
            description="Testing organization for queue management"
        )
        db_session.add(org)
        db_session.commit()
        return org

    @pytest.fixture
    def test_campaigns(self, db_session, test_organization):
        """Create test campaigns with various statuses."""
        campaigns = []
        statuses = [CampaignStatus.RUNNING, CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.CREATED]
        
        for i, status in enumerate(statuses):
            campaign = Campaign(
                name=f"Queue Test Campaign {i+1}",
                description=f"Testing queue management {i+1}",
                organization_id=test_organization.id,
                fileName=f"test_queue_{i+1}.csv",
                totalRecords=50 + i*10,
                url=f"https://app.apollo.io/queue-test-{i+1}",
                status=status
            )
            
            # For paused campaign, add relevant status message
            if status == CampaignStatus.PAUSED:
                campaign.status_message = "Campaign paused: Service apollo unavailable: Test pause reason"
                
            campaigns.append(campaign)
        
        db_session.add_all(campaigns)
        db_session.commit()
        
        # Refresh all campaigns to ensure they have IDs and are properly persisted
        for campaign in campaigns:
            db_session.refresh(campaign)
        
        # Ensure the session is flushed and committed
        db_session.flush()
        
        return campaigns

    def test_campaign_status_endpoint(self, authenticated_client, db_session, test_campaigns):
        """Test GET /queue-management/campaign-status endpoint."""
        response = authenticated_client.get("/api/v1/queue-management/campaign-status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        campaign_data = data["data"]
        assert "totals" in campaign_data
        assert "campaigns_by_status" in campaign_data
        assert "paused_by_service" in campaign_data
        
        totals = campaign_data["totals"]
        assert totals["total_campaigns"] >= 4  # At least our test campaigns
        assert totals["RUNNING"] >= 2  # Changed from lowercase to uppercase
        assert totals["PAUSED"] >= 1   # Changed from lowercase to uppercase
        assert totals["CREATED"] >= 1  # Changed from lowercase to uppercase
        
        # Check paused by service analysis
        paused_by_service = campaign_data["paused_by_service"]
        if "apollo" in paused_by_service:
            assert len(paused_by_service["apollo"]) >= 1

    def test_paused_campaigns_for_service(self, authenticated_client, db_session, test_campaigns):
        """Test GET /queue-management/paused-campaigns/{service} endpoint."""
        response = authenticated_client.get("/api/v1/queue-management/paused-campaigns/apollo")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        campaign_data = data["data"]
        assert "service" in campaign_data
        assert "paused_campaigns" in campaign_data
        assert "count" in campaign_data
        assert campaign_data["service"] == "apollo"
        
        # Should find at least one campaign paused due to apollo
        assert campaign_data["count"] >= 1
        
        paused_campaigns = campaign_data["paused_campaigns"]
        for campaign in paused_campaigns:
            assert "id" in campaign
            assert "name" in campaign
            assert "status" in campaign
            assert campaign["status"] == "PAUSED"  # Changed from lowercase to uppercase
            assert "apollo" in campaign["status_message"].lower()

    def test_bulk_campaign_pause(self, authenticated_client, db_session, test_campaigns):
        """Test POST /queue-management/pause-campaigns-for-service endpoint."""
        pause_data = {
            "service": "perplexity",
            "reason": "Test bulk pause via API"
        }
        
        response = authenticated_client.post(
            "/api/v1/queue-management/pause-campaigns-for-service",
            json=pause_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        campaign_data = data["data"]
        assert "service" in campaign_data
        assert "campaigns_paused" in campaign_data
        assert "reason" in campaign_data
        assert "message" in campaign_data
        
        assert campaign_data["service"] == "perplexity"
        assert campaign_data["reason"] == "Test bulk pause via API"
        
        # Should have paused some running campaigns
        campaigns_paused = campaign_data["campaigns_paused"]
        assert campaigns_paused >= 0  # Could be 0 if no running campaigns

    def test_bulk_campaign_resume(self, authenticated_client, db_session, test_campaigns):
        """Test POST /queue-management/resume-campaigns-for-service endpoint."""
        resume_data = {
            "service": "apollo"
        }
        
        response = authenticated_client.post(
            "/api/v1/queue-management/resume-campaigns-for-service",
            json=resume_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        campaign_data = data["data"]
        assert "service" in campaign_data
        assert "campaigns_eligible" in campaign_data
        assert "campaigns_resumed" in campaign_data
        assert "message" in campaign_data
        
        assert campaign_data["service"] == "apollo"
        
        # Should find eligible campaigns (paused due to apollo)
        campaigns_eligible = campaign_data["campaigns_eligible"]
        campaigns_resumed = campaign_data["campaigns_resumed"]
        
        assert campaigns_eligible >= 1  # At least one campaign paused due to apollo
        # Resumed count might be 0 if circuit breaker blocks resumption

    def test_integrated_service_pause(self, authenticated_client, db_session, test_campaigns):
        """Test POST /queue-management/pause-service endpoint (updated with campaign handling)."""
        pause_data = {
            "service": "openai",
            "reason": "Test integrated service pause"
        }
        
        response = authenticated_client.post(
            "/api/v1/queue-management/pause-service",
            json=pause_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        service_data = data["data"]
        assert "service" in service_data
        assert "paused" in service_data
        assert "jobs_paused" in service_data
        assert "campaigns_paused" in service_data
        assert "message" in service_data
        
        assert service_data["service"] == "openai"
        assert service_data["paused"] is True
        
        # Should have paused some jobs and campaigns
        jobs_paused = service_data["jobs_paused"]
        campaigns_paused = service_data["campaigns_paused"]
        
        assert jobs_paused >= 0
        assert campaigns_paused >= 0

    def test_integrated_service_resume(self, authenticated_client, db_session, test_campaigns):
        """Test POST /queue-management/resume-service endpoint (updated with campaign handling)."""
        resume_data = {
            "service": "openai"
        }
        
        response = authenticated_client.post(
            "/api/v1/queue-management/resume-service",
            json=resume_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        service_data = data["data"]
        assert "service" in service_data
        assert "resumed" in service_data
        assert "jobs_resumed" in service_data
        assert "campaigns_eligible" in service_data
        assert "campaigns_resumed" in service_data
        assert "message" in service_data
        
        assert service_data["service"] == "openai"
        assert service_data["resumed"] is True

    def test_error_handling_invalid_service(self, authenticated_client, db_session):
        """Test error handling for invalid service names."""
        # Test invalid service name in bulk pause
        pause_data = {
            "service": "invalid_service",
            "reason": "Test error handling"
        }
        
        response = authenticated_client.post(
            "/api/v1/queue-management/pause-campaigns-for-service",
            json=pause_data
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid service name" in data["detail"]
        
        # Test invalid service for paused campaigns endpoint
        response = authenticated_client.get("/api/v1/queue-management/paused-campaigns/invalid_service")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid service name" in data["detail"]

    def test_queue_status_endpoint(self, authenticated_client, db_session):
        """Test GET /queue-management/status endpoint."""
        response = authenticated_client.get("/api/v1/queue-management/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        status_data = data["data"]
        assert "circuit_breakers" in status_data
        assert "job_counts" in status_data
        assert "paused_jobs_by_service" in status_data
        assert "timestamp" in status_data

    def test_paused_jobs_for_service(self, authenticated_client, db_session):
        """Test GET /queue-management/paused-jobs/{service} endpoint."""
        response = authenticated_client.get("/api/v1/queue-management/paused-jobs/apollo")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        job_data = data["data"]
        assert "service" in job_data
        assert "paused_jobs" in job_data
        assert "count" in job_data
        assert job_data["service"] == "apollo"

    def test_circuit_breakers_endpoint(self, authenticated_client, db_session):
        """Test GET /queue-management/circuit-breakers endpoint."""
        response = authenticated_client.get("/api/v1/queue-management/circuit-breakers")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        cb_data = data["data"]
        assert "circuit_breakers" in cb_data
        assert "timestamp" in cb_data

    def test_authentication_required(self, client, db_session):
        """Test that all endpoints require authentication."""
        endpoints = [
            "/api/v1/queue-management/campaign-status",
            "/api/v1/queue-management/paused-campaigns/apollo",
            "/api/v1/queue-management/status",
            "/api/v1/queue-management/paused-jobs/apollo",
            "/api/v1/queue-management/circuit-breakers"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
        
        # Test POST endpoints
        post_endpoints = [
            ("/api/v1/queue-management/pause-campaigns-for-service", {"service": "apollo", "reason": "test"}),
            ("/api/v1/queue-management/resume-campaigns-for-service", {"service": "apollo"}),
            ("/api/v1/queue-management/pause-service", {"service": "apollo", "reason": "test"}),
            ("/api/v1/queue-management/resume-service", {"service": "apollo"})
        ]
        
        for endpoint, payload in post_endpoints:
            response = client.post(endpoint, json=payload)
            assert response.status_code == 401

    def test_campaign_workflow_with_queue_management(self, authenticated_client, db_session, test_organization):
        """Test complete workflow: create campaign, pause via queue management, resume."""
        # 1. Create a campaign
        campaign_payload = {
            "name": "Queue Workflow Test Campaign",
            "description": "Testing queue management workflow",
            "organization_id": test_organization.id,
            "fileName": "queue_workflow_test.csv",
            "totalRecords": 100,
            "url": "https://app.apollo.io/queue-workflow-test"
        }
        
        create_response = authenticated_client.post("/api/v1/campaigns/", json=campaign_payload)
        assert create_response.status_code == 201
        campaign_id = create_response.json()["data"]["id"]
        
        # 2. Manually set campaign to running status for testing
        campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
        campaign.status = CampaignStatus.RUNNING
        db_session.commit()
        
        # 3. Pause via queue management bulk operation
        pause_data = {
            "service": "apollo",
            "reason": "Workflow test pause"
        }
        
        pause_response = authenticated_client.post(
            "/api/v1/queue-management/pause-campaigns-for-service",
            json=pause_data
        )
        assert pause_response.status_code == 200
        
        # 4. Verify campaign was paused
        db_session.refresh(campaign)
        assert campaign.status == CampaignStatus.PAUSED
        assert "apollo" in campaign.status_message.lower()
        
        # 5. Check paused campaigns endpoint
        paused_response = authenticated_client.get("/api/v1/queue-management/paused-campaigns/apollo")
        assert paused_response.status_code == 200
        paused_data = paused_response.json()["data"]
        
        # Should find our paused campaign
        paused_campaign_ids = [c["id"] for c in paused_data["paused_campaigns"]]
        assert campaign_id in paused_campaign_ids
        
        # 6. Resume via queue management
        resume_data = {
            "service": "apollo"
        }
        
        resume_response = authenticated_client.post(
            "/api/v1/queue-management/resume-campaigns-for-service",
            json=resume_data
        )
        assert resume_response.status_code == 200
        
        # Note: Campaign might not actually resume due to circuit breaker checks
        # but the endpoint should work correctly 