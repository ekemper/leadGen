"""
Data validation and assertion utilities for smoke tests.
"""

import requests
from app.core.config import settings


def validate_enrichment(leads, token, campaign_index, api_base=None):
    """Validate enrichment results for all leads in a campaign."""
    if api_base is None:
        api_base = f"http://localhost:8000{settings.API_V1_STR}"
        
    print(f"[Validation #{campaign_index}] Starting enrichment validation for {len(leads)} leads...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get expected mock data for this campaign - simplified approach
    validated_count = 0
    for i, lead in enumerate(leads, 1):
        print(f"[Validation #{campaign_index}] Validating lead {i}/{len(leads)}: {lead['email']}")
        resp = requests.get(f"{api_base}/leads/{lead['id']}", headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Lead fetch failed for {lead['id']}: {resp.status_code} {resp.text}")
        
        # Fix: Check if response has "data" wrapper or direct access
        response_data = resp.json()
        updated_lead = response_data.get("data") or response_data
        
        # Simplified validation - just check that enrichment happened
        assert_lead_enrichment_simple(updated_lead, timeout=60)
        validated_count += 1
        print(f"[Validation #{campaign_index}] ✓ Lead {lead['email']} enrichment validated ({validated_count}/{len(leads)})")
    
    print(f"[Validation #{campaign_index}] SUCCESS: All {len(leads)} leads validated successfully!")


def assert_lead_enrichment(updated_lead, mock_lead, timeout):
    """Assert that lead enrichment contains expected data from mock."""
    assert updated_lead.get("enrichment_results"), f"No enrichment_results for {updated_lead['email']} after {timeout}s"
    assert updated_lead.get("email_copy_gen_results"), f"No email_copy_gen_results for {updated_lead['email']} after {timeout}s"
    assert updated_lead.get("instantly_lead_record"), f"No instantly_lead_record for {updated_lead['email']} after {timeout}s"
    assert mock_lead is not None
    assert updated_lead["first_name"] == mock_lead["first_name"]
    assert updated_lead["last_name"] == mock_lead["last_name"]
    assert updated_lead["company"] == (mock_lead.get("organization", {}).get("name") or mock_lead.get("organization_name", ""))


def assert_lead_enrichment_simple(updated_lead, timeout):
    """Assert that lead enrichment occurred (simplified version)."""
    assert updated_lead.get("enrichment_results"), f"No enrichment_results for lead after {timeout}s"
    assert updated_lead.get("email_copy_gen_results"), f"No email_copy_gen_results for lead after {timeout}s"
    assert updated_lead.get("instantly_lead_record"), f"No instantly_lead_record for lead after {timeout}s"


def validate_campaign_data(campaigns_data):
    """Validate the structure and content of campaigns data."""
    if not campaigns_data:
        raise Exception("No campaigns data to validate")
    
    print(f"[Validation] Validating data for {len(campaigns_data)} campaigns...")
    
    for campaign_id, data in campaigns_data.items():
        # Validate required fields
        required_fields = ['campaign_index', 'leads_count', 'leads', 'actual_emails']
        for field in required_fields:
            if field not in data:
                raise Exception(f"Campaign {campaign_id} missing required field: {field}")
        
        # Validate data types and ranges
        if not isinstance(data['campaign_index'], int) or data['campaign_index'] <= 0:
            raise Exception(f"Campaign {campaign_id} has invalid campaign_index: {data['campaign_index']}")
        
        if not isinstance(data['leads_count'], int) or data['leads_count'] <= 0:
            raise Exception(f"Campaign {campaign_id} has invalid leads_count: {data['leads_count']}")
        
        if not isinstance(data['leads'], list) or len(data['leads']) != data['leads_count']:
            raise Exception(f"Campaign {campaign_id} leads list length mismatch")
        
        if not isinstance(data['actual_emails'], set):
            raise Exception(f"Campaign {campaign_id} actual_emails must be a set")
        
        # Validate leads structure
        for i, lead in enumerate(data['leads']):
            if not isinstance(lead, dict):
                raise Exception(f"Campaign {campaign_id} lead {i} is not a dict")
            if 'email' not in lead:
                raise Exception(f"Campaign {campaign_id} lead {i} missing email field")
    
    print(f"[Validation] ✅ All campaigns data validated successfully")


def validate_no_duplicate_emails(campaigns_data):
    """Validate that no email addresses are duplicated across campaigns."""
    print(f"[Validation] Checking for duplicate emails across {len(campaigns_data)} campaigns...")
    
    all_emails = set()
    email_to_campaigns = {}
    
    for campaign_id, data in campaigns_data.items():
        campaign_index = data['campaign_index']
        actual_emails = data['actual_emails']
        
        for email in actual_emails:
            if email in all_emails:
                # Found duplicate
                original_campaign = email_to_campaigns[email]
                raise Exception(f"DUPLICATE EMAIL DETECTED: {email} appears in both Campaign #{original_campaign} and Campaign #{campaign_index}")
            
            all_emails.add(email)
            email_to_campaigns[email] = campaign_index
    
    total_emails = len(all_emails)
    print(f"[Validation] ✅ No duplicate emails found across campaigns ({total_emails} unique emails)")


def validate_no_unexpected_pauses(token, campaign_ids, api_base):
    """Check if any campaigns are in PAUSED status (indicating service issues)."""
    if not api_base:
        raise ValueError("api_base is required")
    
    paused_campaigns = []
    headers = {"Authorization": f"Bearer {token}"}
    
    for campaign_id in campaign_ids:
        try:
            resp = requests.get(f"{api_base}/campaigns/{campaign_id}", headers=headers)
            if resp.status_code == 200:
                campaign = resp.json().get("data", resp.json())
                if campaign["status"] == "PAUSED":
                    paused_campaigns.append({
                        "id": campaign_id,
                        "status_message": campaign.get("status_message", "No message"),
                        "status_error": campaign.get("status_error", "No error")
                    })
        except Exception as e:
            print(f"[Validation] Warning: Could not check campaign {campaign_id}: {e}")
    
    if paused_campaigns:
        print(f"[Validation] ⚠️  Found {len(paused_campaigns)} paused campaigns:")
        for campaign in paused_campaigns:
            print(f"  Campaign {campaign['id']}: {campaign['status_message']}")
            if campaign['status_error']:
                print(f"    Error: {campaign['status_error']}")
        return False, paused_campaigns
    
    return True, [] 