"""
Circuit breaker monitoring utilities for smoke tests.
"""

import requests
from app.core.config import settings


def check_circuit_breaker_status(token, api_base):
    """Check the current status of all circuit breakers."""
    if not api_base:
        raise ValueError("api_base is required")
        
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        resp = requests.get(f"{api_base}/queue/circuit-breaker-status", headers=headers)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[Circuit Breaker] Status check failed: {resp.status_code}")
            return None
    except Exception as e:
        print(f"[Circuit Breaker] Status check error: {e}")
        return None


def check_campaigns_paused_by_circuit_breaker(token, campaign_ids, api_base):
    """Check if any campaigns were paused due to circuit breaker triggers."""
    if not api_base:
        raise ValueError("api_base is required")
        
    headers = {"Authorization": f"Bearer {token}"}
    paused_campaigns = []
    
    for campaign_id in campaign_ids:
        try:
            resp = requests.get(f"{api_base}/campaigns/{campaign_id}", headers=headers)
            if resp.status_code == 200:
                campaign = resp.json().get("data", resp.json())
                if campaign["status"] == "PAUSED" and "circuit breaker" in campaign.get("status_message", "").lower():
                    paused_campaigns.append({
                        "id": campaign_id,
                        "status_message": campaign.get("status_message", ""),
                        "status_error": campaign.get("status_error", "")
                    })
        except Exception as e:
            print(f"[Circuit Breaker] Warning: Could not check campaign {campaign_id}: {e}")
    
    return paused_campaigns


def report_circuit_breaker_failure(cb_status, paused_campaigns):
    """Report detailed circuit breaker failure information."""
    print("\n🔴 CIRCUIT BREAKER TRIGGERED - SERVICE FAILURE DETECTED")
    print("=" * 60)
    
    if cb_status and cb_status.get("data"):
        circuit_breaker = cb_status["data"]
        print(f"Global Circuit Breaker Status:")
        
        if isinstance(circuit_breaker, dict) and "state" in circuit_breaker:
            state = circuit_breaker["state"]
            print(f"  🔴 GLOBAL CIRCUIT BREAKER: {state.upper()}")
            if circuit_breaker.get("last_failure_reason"):
                print(f"    Reason: {circuit_breaker['last_failure_reason']}")
            if circuit_breaker.get("failure_count", 0) > 0:
                print(f"    Failures: {circuit_breaker['failure_count']}/{circuit_breaker.get('failure_threshold', 'unknown')}")
    
    if paused_campaigns:
        print(f"\nCampaigns Paused: {len(paused_campaigns)}")
        for campaign in paused_campaigns:
            print(f"  - Campaign {campaign['id']}: {campaign['status_message']}")
    
    print("\n💡 This indicates legitimate service failures were detected")
    print("💡 The test infrastructure correctly identified and responded to service issues")
    print("=" * 60) 