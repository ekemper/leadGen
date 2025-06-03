"""
Circuit breaker monitoring utilities for smoke tests.
"""

import requests
from app.core.config import settings


def check_circuit_breaker_status(token, api_base=None):
    """Check current circuit breaker status for all services."""
    if api_base is None:
        api_base = f"http://localhost:8000{settings.API_V1_STR}"
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{api_base}/queue-management/status", headers=headers)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[Circuit Breaker] Warning: Could not get status: {resp.status_code}")
            return None
    except Exception as e:
        print(f"[Circuit Breaker] Warning: Status check failed: {e}")
        return None


def check_campaigns_paused_by_circuit_breaker(token, campaign_ids, api_base=None):
    """Check if any campaigns have been paused due to circuit breaker events."""
    if api_base is None:
        api_base = f"http://localhost:8000{settings.API_V1_STR}"
        
    headers = {"Authorization": f"Bearer {token}"}
    paused_campaigns = []
    
    for campaign_id in campaign_ids:
        try:
            resp = requests.get(f"{api_base}/campaigns/{campaign_id}", headers=headers)
            if resp.status_code == 200:
                campaign = resp.json().get("data", resp.json())
                if campaign["status"] == "PAUSED":
                    paused_campaigns.append({
                        "id": campaign_id,
                        "status_message": campaign.get("status_message", ""),
                        "paused_reason": campaign.get("status_error", "")
                    })
        except Exception as e:
            print(f"[Circuit Breaker] Warning: Could not check campaign {campaign_id}: {e}")
    
    return paused_campaigns


def report_circuit_breaker_failure(cb_status, paused_campaigns):
    """Generate clear report when circuit breaker causes test failure."""
    print("\n" + "="*80)
    print("❌ TEST STOPPED: CIRCUIT BREAKER TRIGGERED")
    print("="*80)
    
    if cb_status and cb_status.get("data", {}).get("circuit_breakers"):
        print("\n🔍 Circuit Breaker Status:")
        circuit_breakers = cb_status["data"]["circuit_breakers"]
        
        # Show services that are not in normal 'closed' state
        unhealthy_services = []
        for service, status in circuit_breakers.items():
            if isinstance(status, dict):
                state = status.get("circuit_state", "unknown")
                if state != "closed":
                    unhealthy_services.append((service, status))
                    print(f"  ⚠️  {service.upper()}: {state}")
                    if status.get("pause_info"):
                        print(f"      Reason: {status['pause_info']}")
                    if status.get("failure_count", 0) > 0:
                        print(f"      Failures: {status['failure_count']}/{status.get('failure_threshold', 'unknown')}")
        
        if not unhealthy_services:
            print("  ℹ️  All circuit breakers show 'closed' state")
            print("  ℹ️  Campaigns may have been paused by previous failures or manual intervention")
    
    if paused_campaigns:
        print(f"\n📊 Campaigns Paused: {len(paused_campaigns)}")
        for campaign in paused_campaigns:
            print(f"  🛑 Campaign {campaign['id']}")
            if campaign["status_message"]:
                print(f"      Message: {campaign['status_message']}")
            if campaign["paused_reason"]:
                print(f"      Reason: {campaign['paused_reason']}")
    
    print("\n💡 This indicates a real service failure occurred during testing.")
    print("💡 Check service health and retry the test when services are restored.")
    print("="*80) 