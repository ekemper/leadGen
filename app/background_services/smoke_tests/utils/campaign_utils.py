"""
Campaign management utilities for smoke tests.
"""

import requests
from app.core.config import settings


def create_campaign(token, campaign_index, organization_id=None, leads_per_campaign=20, api_base=None):
    """
    Create a new campaign.
    
    Args:
        token: Authentication token
        campaign_index: Index number for campaign naming
        organization_id: Optional organization ID
        leads_per_campaign: Number of leads per campaign
        api_base: API base URL, defaults to settings-based URL
        
    Returns:
        str: Campaign ID
    """
    if api_base is None:
        api_base = f"http://localhost:8000{settings.API_V1_STR}"
    
    # No longer need to set campaign index for mock client - pop-based approach handles this automatically
    
    campaign_data = {
        "name": f"Concurrent Test Campaign #{campaign_index}",
        "description": f"Campaign #{campaign_index} for testing concurrent Apify mock integration.",
        "fileName": f"mock-file-{campaign_index}.csv",
        "totalRecords": leads_per_campaign,
        "url": "https://app.apollo.io/#/people?contactEmailStatusV2%5B%5D=verified&contactEmailExcludeCatchAll=true&personTitles%5B%5D=CEO&personTitles%5B%5D=Founder&page=1"
    }
    if organization_id:
        campaign_data["organization_id"] = organization_id
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[Campaign #{campaign_index}] Creating campaign...")
    resp = requests.post(f"{api_base}/campaigns", json=campaign_data, headers=headers)
    if resp.status_code != 201:
        print(f"[Campaign #{campaign_index}] Creation failed: {resp.status_code} {resp.text}")
        raise Exception(f"Campaign #{campaign_index} creation failed")

    # Fix: Check if response has "data" wrapper or direct access
    response_data = resp.json()
    campaign_id = response_data.get("data", {}).get("id") or response_data.get("id")
    
    # No longer need to register campaign mapping - pop-based approach is automatic
    
    print(f"[Campaign #{campaign_index}] Created campaign with id: {campaign_id}")
    return campaign_id


def start_campaign(token, campaign_id, campaign_index, api_base=None):
    """
    Start a campaign.
    
    Args:
        token: Authentication token
        campaign_id: Campaign ID to start
        campaign_index: Index number for logging
        api_base: API base URL, defaults to settings-based URL
    """
    if api_base is None:
        api_base = f"http://localhost:8000{settings.API_V1_STR}"
        
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[Campaign #{campaign_index}] Starting campaign {campaign_id}...")
    resp = requests.post(f"{api_base}/campaigns/{campaign_id}/start", json={}, headers=headers)
    if resp.status_code != 200:
        print(f"[Campaign #{campaign_index}] Start failed: {resp.status_code} {resp.text}")
        raise Exception(f"Campaign #{campaign_index} start failed")
    print(f"[Campaign #{campaign_index}] Started campaign {campaign_id}")


def get_all_leads(token, campaign_id, campaign_index, api_base=None):
    """
    Fetch all leads for a campaign.
    
    Args:
        token: Authentication token
        campaign_id: Campaign ID
        campaign_index: Index number for logging
        api_base: API base URL, defaults to settings-based URL
        
    Returns:
        list: List of lead objects
    """
    if api_base is None:
        api_base = f"http://localhost:8000{settings.API_V1_STR}"
        
    print(f"[API #{campaign_index}] Fetching all leads for campaign {campaign_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{api_base}/leads", headers=headers, params={"campaign_id": campaign_id})
    if resp.status_code != 200:
        raise Exception(f"Leads fetch failed for campaign #{campaign_index}: {resp.status_code} {resp.text}")
    
    # Fix: Check if response has "data" wrapper or direct access
    response_data = resp.json()
    leads_data = response_data.get("data", {}).get("leads") or response_data.get("leads", [])
    print(f"[API #{campaign_index}] Successfully retrieved {len(leads_data)} leads")
    return leads_data


def create_campaigns_sequentially(token, organization_id, num_campaigns, leads_per_campaign, wait_for_jobs_func, validate_no_duplicate_emails_func, api_base=None):
    """Create and start campaigns one by one, focusing on process validation rather than content prediction."""
    if api_base is None:
        api_base = f"http://localhost:8000{settings.API_V1_STR}"
        
    campaigns_data = {}
    
    print(f"[Setup] Creating {num_campaigns} campaigns sequentially...")
    
    for campaign_index in range(1, num_campaigns + 1):
        print(f"\n[Setup] === Setting up Campaign #{campaign_index} ===")
        
        # Create and start campaign (no email prediction needed with pop-based approach)
        campaign_id = create_campaign(token, campaign_index, organization_id, leads_per_campaign, api_base)
        start_campaign(token, campaign_id, campaign_index, api_base)
        
        # Wait for FETCH_LEADS to complete before moving to next campaign
        print(f"[Setup] Waiting for Campaign #{campaign_index} FETCH_LEADS to complete...")
        wait_for_jobs_func(token, campaign_id, "FETCH_LEADS", campaign_index, expected_count=1, timeout=180, api_base=api_base)
        
        # Get leads and validate that we got some leads
        leads = get_all_leads(token, campaign_id, campaign_index, api_base)
        actual_emails = {lead["email"] for lead in leads if lead["email"]}
        
        print(f"[Debug] Campaign #{campaign_index} received {len(leads)} leads with {len(actual_emails)} valid emails")
        
        # SIMPLIFIED VALIDATION: Just check we got leads
        if len(leads) == 0:
            raise Exception(f"Campaign #{campaign_index} got no leads from mock!")
        
        if len(actual_emails) == 0:
            raise Exception(f"Campaign #{campaign_index} got no valid email addresses!")
        
        print(f"[Setup] ✅ Campaign #{campaign_index} ready with {len(leads)} leads ({len(actual_emails)} valid emails)")
        
        # Store campaign tracking data for process validation
        campaigns_data[campaign_id] = {
            'campaign_index': campaign_index,
            'leads_count': len(leads),
            'leads': leads,
            'actual_emails': actual_emails
        }
    
    print(f"\n[Setup] ✅ All {num_campaigns} campaigns created successfully!")
    
    # CROSS-CAMPAIGN VALIDATION: Ensure no duplicate emails across campaigns
    validate_no_duplicate_emails_func(campaigns_data)
    
    return campaigns_data 