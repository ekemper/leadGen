import os
import sys
# Ensure project root is in sys.path for 'server' imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ["USE_APIFY_CLIENT_MOCK"] = "true"
import requests
import time
import random
import string

API_BASE = "http://localhost:5001/api"

# Utility to generate a random email for test user
def random_email():
    return f"testuser_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}@example.com"

def signup_and_login():
    email = random_email()
    password = "Test1234!"
    signup_data = {
        "email": email,
        "password": password,
        "confirm_password": password
    }
    print(f"[Auth] Signing up test user: {email}")
    resp = requests.post(f"{API_BASE}/auth/signup", json=signup_data)
    if resp.status_code not in (200, 201):
        print(f"[Auth] Signup failed: {resp.status_code} {resp.text}")
        raise Exception("Signup failed")
    print(f"[Auth] Signing in test user: {email}")
    resp = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        print(f"[Auth] Login failed: {resp.status_code} {resp.text}")
        raise Exception("Login failed")
    token = resp.json()["data"]["token"]
    print(f"[Auth] Got token: {token[:8]}...")
    return token

def create_organization(token):
    headers = {"Authorization": f"Bearer {token}"}
    org_data = {
        "name": "Test Org",
        "description": "A test organization."
    }
    resp = requests.post(f"{API_BASE}/organizations", json=org_data, headers=headers)
    if resp.status_code != 201:
        print(f"[Org] Creation failed: {resp.status_code} {resp.text}")
        raise Exception("Organization creation failed")
    org_id = resp.json()["data"]["id"]
    print(f"[Org] Created organization with id: {org_id}")
    return org_id

def create_campaign(token, organization_id=None):
    from server.background_services.mock_apify_client import MOCK_LEADS_DATA
    campaign_data = {
        "name": "Mock Test Campaign",
        "description": "A campaign for testing the Apify mock integration.",
        "fileName": "mock-file.csv",
        "totalRecords": 10,
        "url": "https://mock-apollo-search-url.com"
    }
    if organization_id:
        campaign_data["organization_id"] = organization_id
    headers = {"Authorization": f"Bearer {token}"}
    print("[Campaign] Creating campaign...")
    resp = requests.post(f"{API_BASE}/campaigns", json=campaign_data, headers=headers)
    if resp.status_code != 201:
        print(f"[Campaign] Creation failed: {resp.status_code} {resp.text}")
        raise Exception("Campaign creation failed")
    campaign_id = resp.json()["data"]["id"]
    print(f"[Campaign] Created campaign with id: {campaign_id}")
    return campaign_id

def start_campaign(token, campaign_id):
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[Campaign] Starting campaign {campaign_id}...")
    resp = requests.post(f"{API_BASE}/campaigns/{campaign_id}/start", json={}, headers=headers)
    if resp.status_code != 200:
        print(f"[Campaign] Start failed: {resp.status_code} {resp.text}")
        raise Exception("Campaign start failed")
    print(f"[Campaign] Started campaign {campaign_id}")

def poll_leads(token, campaign_id, expected_count, timeout=60):
    headers = {"Authorization": f"Bearer {token}"}
    waited = 0
    interval = 2
    print(f"[Leads] Polling for leads for campaign {campaign_id}...")
    while waited < timeout:
        resp = requests.get(f"{API_BASE}/leads", headers=headers, params={"campaign_id": campaign_id})
        if resp.status_code != 200:
            print(f"[Leads] Error: {resp.status_code} {resp.text}")
            raise Exception("Leads fetch failed")
        leads = resp.json()["data"]["leads"]
        print(f"[Leads] Waited {waited}s: Found {len(leads)}/{expected_count} leads...")
        if len(leads) >= expected_count:
            print(f"[Leads] All leads found after {waited}s.")
            return leads
        time.sleep(interval)
        waited += interval
    raise Exception(f"Timeout: Only found {len(leads)} leads after {timeout}s")

def fetch_campaign_jobs(api_base, campaign_id, headers):
    resp = requests.get(f"{api_base}/jobs", headers=headers, params={"campaign_id": campaign_id})
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch jobs for campaign {campaign_id}: {resp.status_code} {resp.text}")
    return resp.json()["data"]["jobs"]

def build_enrichment_job_dict(jobs):
    return {
        job["parameters"]["lead_id"]: job
        for job in jobs
        if job.get("job_type") == "ENRICH_LEAD" and job.get("parameters") and job["parameters"].get("lead_id")
    }

def poll_job_completion(lead, campaign_id, headers, api_base, timeout, interval=4):
    waited = 0
    while waited < timeout:
        jobs = fetch_campaign_jobs(api_base, campaign_id, headers)
        enrichment_jobs_by_lead_id = build_enrichment_job_dict(jobs)
        enrichment_job = enrichment_jobs_by_lead_id.get(lead["id"])
        if not enrichment_job:
            raise Exception(f"No enrichment job found for lead {lead['email']} (id={lead['id']})")
        status = enrichment_job.get("status")
        print(f"[Enrichment] Waited {waited}s for job {enrichment_job['id']}... status: {status}")
        if status in ("COMPLETED", "FAILED"):
            return enrichment_job
        time.sleep(interval)
        waited += interval
    raise Exception(f"Timeout waiting for enrichment job for lead {lead['email']}")

def assert_lead_enrichment(updated_lead, mock_lead, timeout):
    assert updated_lead.get("enrichment_results"), f"No enrichment_results for {updated_lead['email']} after {timeout}s"
    assert updated_lead.get("email_copy_gen_results"), f"No email_copy_gen_results for {updated_lead['email']} after {timeout}s"
    assert updated_lead.get("instantly_lead_record"), f"No instantly_lead_record for {updated_lead['email']} after {timeout}s"
    assert mock_lead is not None
    assert updated_lead["first_name"] == mock_lead["first_name"]
    assert updated_lead["last_name"] == mock_lead["last_name"]
    assert updated_lead["company"] == (mock_lead.get("organization", {}).get("name") or mock_lead.get("organization_name", ""))

def poll_enrichment(leads, token, campaign_id, timeout=240):
    headers = {"Authorization": f"Bearer {token}"}
    from server.background_services.mock_apify_client import MOCK_LEADS_DATA
    API_BASE = "http://localhost:5001/api"
    jobs = fetch_campaign_jobs(API_BASE, campaign_id, headers)
    enrichment_jobs_by_lead_id = build_enrichment_job_dict(jobs)
    for lead in leads:
        enrichment_job = enrichment_jobs_by_lead_id.get(lead["id"])
        if not enrichment_job:
            raise Exception(f"No enrichment job found for lead {lead['email']} (id={lead['id']}) in campaign jobs list")
        enrichment_job = poll_job_completion(lead, campaign_id, headers, API_BASE, timeout, interval=4)
        if enrichment_job["status"] != "COMPLETED":
            raise Exception(f"Enrichment job {enrichment_job['id']} for lead {lead['email']} did not complete successfully. Status: {enrichment_job['status']}, Error: {enrichment_job.get('error_message')}")
        # After job is completed, fetch the lead and assert enrichment fields
        resp = requests.get(f"{API_BASE}/leads/{lead['id']}", headers=headers)
        if resp.status_code != 200:
            print(f"[Leads] Error: {resp.status_code} {resp.text}")
            raise Exception("Lead fetch failed")
        updated_lead = resp.json()["data"]
        mock_lead = next((l for l in MOCK_LEADS_DATA if l["email"] == lead["email"]), None)
        assert_lead_enrichment(updated_lead, mock_lead, timeout)
        print(f"[Enrichment] Lead {lead['email']} enrichment complete.")

def main():
    from server.background_services.mock_apify_client import MOCK_LEADS_DATA
    token = signup_and_login()
    organization_id = create_organization(token)
    campaign_id = create_campaign(token, organization_id=organization_id)
    start_campaign(token, campaign_id)
    leads = poll_leads(token, campaign_id, expected_count=len(MOCK_LEADS_DATA), timeout=60)
    # Assert that the leads match the mock data (by email, name, etc)
    mock_emails = {lead["email"] for lead in MOCK_LEADS_DATA}
    db_emails = {lead["email"] for lead in leads}
    assert mock_emails == db_emails, f"Emails in DB: {db_emails}, expected: {mock_emails}"
    poll_enrichment(leads, token, campaign_id, timeout=240)
    print("\n[Success] All leads ingested and enriched successfully!")

if __name__ == "__main__":
    main() 