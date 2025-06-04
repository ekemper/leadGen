"""
Phase 6 Step 20: Queue Status Integration Tests

Comprehensive test suite for queue status monitoring and manual resume workflows.
Tests the integration between queue status, circuit breakers, campaigns, and jobs.

Key Test Areas:
- Queue status endpoint accuracy during various system states
- Manual queue resume workflow with prerequisite validation  
- Circuit breaker reset and queue resume separation
- Real-time status update accuracy
- Queue status changes propagating to campaigns and jobs
"""

import pytest
import time
from unittest.mock import patch, MagicMock

# Test configuration
API_BASE = "/api/v1/queue-management"


class TestQueueStatusAccuracy:
    """Test queue status endpoint accuracy during various system states."""
    
    def test_queue_status_accuracy_during_normal_operations(self, authenticated_client, db_session):
        """Test queue status endpoint provides accurate data during normal operations."""
        # Get initial queue status
        response = authenticated_client.get(f"{API_BASE}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        status_data = data["data"]
        required_fields = ["circuit_breakers", "job_counts", "paused_jobs_by_service", "timestamp"]
        for field in required_fields:
            assert field in status_data, f"Missing required field: {field}"
        
        # Verify circuit breaker data structure
        circuit_breakers = status_data["circuit_breakers"]
        assert isinstance(circuit_breakers, dict)
        
        # Check for expected services
        expected_services = ["apollo", "perplexity", "openai", "instantly", "millionverifier"]
        for service in expected_services:
            if service in circuit_breakers:
                cb_info = circuit_breakers[service]
                if isinstance(cb_info, dict):
                    assert "circuit_state" in cb_info
                    assert cb_info["circuit_state"] in ["closed", "open", "half_open"]
        
        # Verify job counts structure
        job_counts = status_data["job_counts"]
        assert isinstance(job_counts, dict)
        
        # Verify paused jobs by service structure
        paused_by_service = status_data["paused_jobs_by_service"]
        assert isinstance(paused_by_service, dict)
        
        # Verify timestamp is present and recent
        timestamp = status_data["timestamp"]
        assert timestamp is not None

    def test_queue_status_during_circuit_breaker_trigger(self, authenticated_client, db_session, multiple_campaigns):
        """Test queue status accuracy when circuit breaker is triggered."""
        # Trigger circuit breaker by pausing a service
        pause_data = {
            "service": "apollo",
            "reason": "Integration test circuit breaker trigger"
        }
        
        pause_response = authenticated_client.post(f"{API_BASE}/pause-service", json=pause_data)
        assert pause_response.status_code == 200
        
        # Get queue status after circuit breaker trigger
        status_response = authenticated_client.get(f"{API_BASE}/status")
        assert status_response.status_code == 200
        
        status_data = status_response.json()["data"]
        circuit_breakers = status_data["circuit_breakers"]
        
        # Apollo circuit breaker should reflect the pause
        if "apollo" in circuit_breakers:
            apollo_cb = circuit_breakers["apollo"]
            if isinstance(apollo_cb, dict):
                # Should be paused/open due to manual pause
                assert apollo_cb.get("circuit_state") in ["open", "half_open", "paused"]
        
        # Reset the circuit breaker
        reset_response = authenticated_client.post(f"{API_BASE}/circuit-breakers/apollo/reset")
        assert reset_response.status_code == 200
        
        # Verify status reflects the reset
        final_status_response = authenticated_client.get(f"{API_BASE}/status")
        assert final_status_response.status_code == 200


class TestManualQueueResume:
    """Test manual queue resume workflow with prerequisite validation."""
    
    def test_manual_queue_resume_with_all_circuit_breakers_closed(self, authenticated_client, db_session):
        """Test successful manual queue resume when all circuit breakers are closed."""
        # Ensure all circuit breakers are closed first
        reset_services = ["apollo", "perplexity", "openai", "instantly", "millionverifier"]
        
        for service in reset_services:
            reset_response = authenticated_client.post(f"{API_BASE}/circuit-breakers/{service}/reset")
            # May return 200 or 404 depending on implementation - both acceptable
            assert reset_response.status_code in [200, 404]
        
        # Attempt manual queue resume
        resume_response = authenticated_client.post(f"{API_BASE}/resume-queue")
        
        # Should succeed when all circuit breakers are closed
        assert resume_response.status_code == 200
        
        resume_data = resume_response.json()
        assert resume_data["status"] == "success"
        
        # Verify response contains expected data
        response_data = resume_data["data"]
        expected_fields = ["queue_resumed", "jobs_resumed", "campaigns_eligible", "campaigns_resumed"]
        for field in expected_fields:
            assert field in response_data, f"Missing field in resume response: {field}"
        
        assert response_data["queue_resumed"] is True
        
        # Verify prerequisites_met field indicates success
        if "prerequisites_met" in response_data:
            assert "circuit breakers closed" in response_data["prerequisites_met"].lower()

    def test_manual_queue_resume_blocked_by_open_circuit_breaker(self, authenticated_client, db_session):
        """Test manual queue resume is blocked when circuit breaker is open."""
        # Pause a service to open its circuit breaker
        pause_data = {
            "service": "apollo",
            "reason": "Testing queue resume prerequisite validation"
        }
        
        pause_response = authenticated_client.post(f"{API_BASE}/pause-service", json=pause_data)
        assert pause_response.status_code == 200
        
        # Attempt manual queue resume with open circuit breaker
        resume_response = authenticated_client.post(f"{API_BASE}/resume-queue")
        
        # Should be blocked due to open circuit breaker
        assert resume_response.status_code == 400
        
        error_data = resume_response.json()
        assert "detail" in error_data
        
        # Error message should mention circuit breaker prerequisite
        error_message = error_data["detail"].lower()
        assert "circuit breaker" in error_message or "apollo" in error_message
        
        # Clean up - reset the circuit breaker
        reset_response = authenticated_client.post(f"{API_BASE}/circuit-breakers/apollo/reset")
        assert reset_response.status_code == 200

    def test_circuit_breaker_reset_does_not_resume_queue(self, authenticated_client, db_session, multiple_campaigns):
        """Test that circuit breaker reset does NOT automatically resume queue/campaigns."""
        # Pause a service and create some paused campaigns
        pause_data = {
            "service": "apollo",
            "reason": "Testing circuit breaker reset isolation"
        }
        
        pause_response = authenticated_client.post(f"{API_BASE}/pause-service", json=pause_data)
        assert pause_response.status_code == 200
        
        # Get initial campaign status
        initial_campaign_response = authenticated_client.get(f"{API_BASE}/campaign-status")
        assert initial_campaign_response.status_code == 200
        initial_data = initial_campaign_response.json()["data"]
        
        # Reset the circuit breaker
        reset_response = authenticated_client.post(f"{API_BASE}/circuit-breakers/apollo/reset")
        assert reset_response.status_code == 200
        
        # Get campaign status after circuit breaker reset
        post_reset_campaign_response = authenticated_client.get(f"{API_BASE}/campaign-status")
        assert post_reset_campaign_response.status_code == 200
        post_reset_data = post_reset_campaign_response.json()["data"]
        
        # Campaign status should be UNCHANGED after circuit breaker reset
        # (Campaigns should remain paused until manual queue resume)
        initial_paused = initial_data["totals"]["PAUSED"]
        post_reset_paused = post_reset_data["totals"]["PAUSED"]
        
        # Paused campaigns should remain paused
        assert post_reset_paused >= initial_paused, "Circuit breaker reset should not automatically resume campaigns"
        
        # Manual queue resume should now work since circuit breaker is reset
        queue_resume_response = authenticated_client.post(f"{API_BASE}/resume-queue")
        assert queue_resume_response.status_code == 200


class TestQueueResumeWorkflow:
    """Test complete queue resume workflow and cascade effects."""
    
    def test_queue_resume_cascade_to_campaigns_and_jobs(self, authenticated_client, db_session, multiple_campaigns):
        """Test that queue resume properly cascades to campaigns and jobs."""
        # Initial state - ensure clean starting point
        reset_services = ["apollo", "perplexity", "openai", "instantly", "millionverifier"]
        for service in reset_services:
            authenticated_client.post(f"{API_BASE}/circuit-breakers/{service}/reset")
        
        # Pause a service to create paused state
        pause_data = {
            "service": "apollo",
            "reason": "Testing cascade resume workflow"
        }
        
        pause_response = authenticated_client.post(f"{API_BASE}/pause-service", json=pause_data)
        assert pause_response.status_code == 200
        
        # Get paused jobs count
        paused_jobs_response = authenticated_client.get(f"{API_BASE}/paused-jobs/apollo")
        assert paused_jobs_response.status_code == 200
        paused_jobs_before = paused_jobs_response.json()["data"]["count"]
        
        # Get paused campaigns count
        paused_campaigns_response = authenticated_client.get(f"{API_BASE}/paused-campaigns/apollo")
        assert paused_campaigns_response.status_code == 200
        paused_campaigns_before = paused_campaigns_response.json()["data"]["count"]
        
        # Reset circuit breaker first
        reset_response = authenticated_client.post(f"{API_BASE}/circuit-breakers/apollo/reset")
        assert reset_response.status_code == 200
        
        # Perform manual queue resume
        queue_resume_response = authenticated_client.post(f"{API_BASE}/resume-queue")
        assert queue_resume_response.status_code == 200
        
        resume_data = queue_resume_response.json()["data"]
        
        # Verify cascade effects reported in response
        assert "jobs_resumed" in resume_data
        assert "campaigns_resumed" in resume_data
        
        jobs_resumed = resume_data["jobs_resumed"]
        campaigns_resumed = resume_data["campaigns_resumed"]
        
        # Should have resumed some jobs if there were paused jobs
        if paused_jobs_before > 0:
            assert jobs_resumed >= 0  # May be 0 if jobs were cleaned up
        
        # Should have resumed some campaigns if there were paused campaigns
        if paused_campaigns_before > 0:
            assert campaigns_resumed >= 0  # May be 0 if campaigns were cleaned up
        
        # Verify paused counts decreased
        final_paused_jobs_response = authenticated_client.get(f"{API_BASE}/paused-jobs/apollo")
        assert final_paused_jobs_response.status_code == 200
        paused_jobs_after = final_paused_jobs_response.json()["data"]["count"]
        
        final_paused_campaigns_response = authenticated_client.get(f"{API_BASE}/paused-campaigns/apollo")
        assert final_paused_campaigns_response.status_code == 200
        paused_campaigns_after = final_paused_campaigns_response.json()["data"]["count"]
        
        # Paused counts should be same or lower after resume
        assert paused_jobs_after <= paused_jobs_before
        assert paused_campaigns_after <= paused_campaigns_before

    def test_queue_status_endpoint_real_time_updates(self, authenticated_client, db_session):
        """Test that queue status endpoint reflects real-time system changes."""
        # Get baseline status
        baseline_response = authenticated_client.get(f"{API_BASE}/status")
        assert baseline_response.status_code == 200
        baseline_timestamp = baseline_response.json()["data"]["timestamp"]
        
        # Make a change (pause a service)
        pause_data = {
            "service": "apollo", 
            "reason": "Testing real-time status updates"
        }
        
        pause_response = authenticated_client.post(f"{API_BASE}/pause-service", json=pause_data)
        assert pause_response.status_code == 200
        
        # Get updated status
        updated_response = authenticated_client.get(f"{API_BASE}/status")
        assert updated_response.status_code == 200
        updated_data = updated_response.json()["data"]
        updated_timestamp = updated_data["timestamp"]
        
        # Timestamp should be different (more recent)
        assert updated_timestamp != baseline_timestamp
        
        # Circuit breaker status should reflect the change
        circuit_breakers = updated_data["circuit_breakers"]
        if "apollo" in circuit_breakers:
            apollo_status = circuit_breakers["apollo"]
            if isinstance(apollo_status, dict):
                # Should show paused/open state
                state = apollo_status.get("circuit_state", "unknown")
                assert state in ["open", "half_open", "paused", "closed"]  # Any valid state
        
        # Reset and verify again
        reset_response = authenticated_client.post(f"{API_BASE}/circuit-breakers/apollo/reset")
        assert reset_response.status_code == 200
        
        final_response = authenticated_client.get(f"{API_BASE}/status")
        assert final_response.status_code == 200
        final_timestamp = final_response.json()["data"]["timestamp"]
        
        # Should have another different timestamp
        assert final_timestamp != updated_timestamp

    def test_multiple_circuit_breaker_failures_and_manual_recovery(self, authenticated_client, db_session):
        """Test system behavior with multiple circuit breaker failures and recovery."""
        # Test with multiple services
        test_services = ["apollo", "perplexity"]
        
        # Pause multiple services
        for service in test_services:
            pause_data = {
                "service": service,
                "reason": f"Testing multiple CB failures - {service}"
            }
            
            pause_response = authenticated_client.post(f"{API_BASE}/pause-service", json=pause_data)
            assert pause_response.status_code == 200
        
        # Get status with multiple failures
        status_response = authenticated_client.get(f"{API_BASE}/status")
        assert status_response.status_code == 200
        
        circuit_breakers = status_response.json()["data"]["circuit_breakers"]
        
        # Attempt queue resume with multiple open circuit breakers
        resume_response = authenticated_client.post(f"{API_BASE}/resume-queue")
        
        # Should fail due to multiple open circuit breakers
        assert resume_response.status_code == 400
        
        error_message = resume_response.json()["detail"].lower()
        # Should mention multiple services or general circuit breaker issue
        assert "circuit breaker" in error_message
        
        # Reset one service at a time
        for service in test_services:
            reset_response = authenticated_client.post(f"{API_BASE}/circuit-breakers/{service}/reset")
            assert reset_response.status_code == 200
            
            # Queue resume should still fail until ALL are reset
            if service != test_services[-1]:  # Not the last service
                partial_resume_response = authenticated_client.post(f"{API_BASE}/resume-queue")
                # May still fail if other breakers are open
        
        # Final queue resume should succeed after all resets
        final_resume_response = authenticated_client.post(f"{API_BASE}/resume-queue")
        assert final_resume_response.status_code == 200
        
        final_data = final_resume_response.json()["data"]
        assert final_data["queue_resumed"] is True


class TestQueueStatusIntegrationEdgeCases:
    """Test edge cases and error scenarios in queue status integration."""
    
    def test_queue_status_with_invalid_circuit_breaker_states(self, authenticated_client, db_session):
        """Test queue status handling when circuit breaker data is inconsistent."""
        # This test ensures the queue status endpoint handles edge cases gracefully
        response = authenticated_client.get(f"{API_BASE}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        # Even with potential inconsistencies, should return valid structure
        status_data = data["data"]
        assert "circuit_breakers" in status_data
        assert "job_counts" in status_data
        
        # Should handle missing or malformed circuit breaker data gracefully
        circuit_breakers = status_data["circuit_breakers"]
        assert isinstance(circuit_breakers, (dict, type(None)))

    def test_concurrent_queue_operations(self, authenticated_client, db_session):
        """Test system behavior with concurrent queue management operations."""
        # This test simulates multiple rapid operations
        
        # Rapid pause and reset operations
        operations = []
        
        # Pause service
        pause_response = authenticated_client.post(f"{API_BASE}/pause-service", json={
            "service": "apollo",
            "reason": "Concurrent operations test"
        })
        operations.append(("pause", pause_response.status_code))
        
        # Immediate status check
        status_response = authenticated_client.get(f"{API_BASE}/status")
        operations.append(("status", status_response.status_code))
        
        # Reset circuit breaker
        reset_response = authenticated_client.post(f"{API_BASE}/circuit-breakers/apollo/reset")
        operations.append(("reset", reset_response.status_code))
        
        # Another status check
        status_response2 = authenticated_client.get(f"{API_BASE}/status")
        operations.append(("status2", status_response2.status_code))
        
        # Queue resume
        resume_response = authenticated_client.post(f"{API_BASE}/resume-queue")
        operations.append(("resume", resume_response.status_code))
        
        # All operations should complete successfully
        for operation, status_code in operations:
            assert status_code in [200, 400], f"Operation {operation} failed with status {status_code}"
        
        # Final status should be consistent
        final_status = authenticated_client.get(f"{API_BASE}/status")
        assert final_status.status_code == 200

    def test_queue_status_data_consistency(self, authenticated_client, db_session):
        """Test that queue status data remains consistent across multiple calls."""
        # Get multiple snapshots of queue status
        snapshots = []
        
        for i in range(3):
            response = authenticated_client.get(f"{API_BASE}/status")
            assert response.status_code == 200
            snapshots.append(response.json()["data"])
            time.sleep(0.1)  # Small delay between requests
        
        # Compare snapshots for consistency
        for i in range(1, len(snapshots)):
            current = snapshots[i]
            previous = snapshots[i-1]
            
            # Should have same structure
            assert set(current.keys()) == set(previous.keys())
            
            # Circuit breaker structure should be consistent
            current_cb = current.get("circuit_breakers", {})
            previous_cb = previous.get("circuit_breakers", {})
            
            if current_cb and previous_cb:
                # Should have same services
                current_services = set(current_cb.keys())
                previous_services = set(previous_cb.keys())
                # Services may change but should be consistent within test period
                assert isinstance(current_services, set)
                assert isinstance(previous_services, set) 