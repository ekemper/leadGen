import os
import sys
# Ensure project root is in sys.path for app imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Enable the Apollo mock but leave Perplexity live
os.environ["USE_APIFY_CLIENT_MOCK"] = "true"  # keep Apollo mocked

import requests
import time
import random
import string
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.database import SessionLocal, get_db
from app.core.config import settings

API_BASE = f"http://localhost:8000{settings.API_V1_STR}"

# Utility to generate a random email for test user
def random_email():
    return f"testuser_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}@hellacooltestingdomain.pizza"

# Use a unique email each run to avoid duplicates
TEST_EMAIL = random_email()

def random_password():
    specials = "!@#$%^&*()"
    # Ensure at least one of each required type
    password = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(specials),
    ]
    # Fill the rest with random choices
    chars = string.ascii_letters + string.digits + specials
    password += random.choices(chars, k=8)
    random.shuffle(password)
    return ''.join(password)

# --------------- Test helpers --------------

def signup_and_login():
    email = TEST_EMAIL
    password = random_password()
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
    
    # Fix: Access token directly from response (no "data" wrapper)
    response_data = resp.json()
    token = response_data["token"]["access_token"]
    print(f"[Auth] Got token: {token[:8]}...")
    return token, email

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
    
    # Fix: Check if response has "data" wrapper or direct access
    response_data = resp.json()
    org_id = response_data.get("data", {}).get("id") or response_data.get("id")
    print(f"[Org] Created organization with id: {org_id}")
    return org_id

def create_campaign(token, organization_id=None):
    from app.background_services.smoke_tests.mock_apify_client import MOCK_LEADS_DATA
    campaign_data = {
        "name": "Mock Test Campaign",
        "description": "A campaign for testing the Apify mock integration.",
        "fileName": "mock-file.csv",
        "totalRecords": 10,
        "url": "https://app.apollo.io/#/people?contactEmailStatusV2%5B%5D=verified&contactEmailExcludeCatchAll=true&personTitles%5B%5D=CEO&personTitles%5B%5D=Founder&page=1"
    }
    if organization_id:
        campaign_data["organization_id"] = organization_id
    headers = {"Authorization": f"Bearer {token}"}
    print("[Campaign] Creating campaign...")
    resp = requests.post(f"{API_BASE}/campaigns", json=campaign_data, headers=headers)
    if resp.status_code != 201:
        print(f"[Campaign] Creation failed: {resp.status_code} {resp.text}")
        raise Exception("Campaign creation failed")
    
    # Fix: Check if response has "data" wrapper or direct access
    response_data = resp.json()
    campaign_id = response_data.get("data", {}).get("id") or response_data.get("id")
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

# After running enrichment jobs synchronously, validate each lead once.

def validate_enrichment(leads, token):
    print(f"[Validation] Starting enrichment validation for {len(leads)} leads...")
    headers = {"Authorization": f"Bearer {token}"}
    from app.background_services.smoke_tests.mock_apify_client import MOCK_LEADS_DATA
    
    validated_count = 0
    for i, lead in enumerate(leads, 1):
        print(f"[Validation] Validating lead {i}/{len(leads)}: {lead['email']}")
        resp = requests.get(f"{API_BASE}/leads/{lead['id']}", headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Lead fetch failed for {lead['id']}: {resp.status_code} {resp.text}")
        
        # Fix: Check if response has "data" wrapper or direct access
        response_data = resp.json()
        updated_lead = response_data.get("data") or response_data
        mock_lead = next((l for l in MOCK_LEADS_DATA if l["email"] == lead["email"]), None)
        assert_lead_enrichment(updated_lead, mock_lead, timeout=60)
        validated_count += 1
        print(f"[Validation] ✓ Lead {lead['email']} enrichment validated ({validated_count}/{len(leads)})")
    
    print(f"[Validation] SUCCESS: All {len(leads)} leads validated successfully!")

# ---------------- Polling utilities ----------------

def fetch_campaign_jobs(token, campaign_id):
    """Return list of jobs for the given campaign via API."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_BASE}/jobs", headers=headers, params={"campaign_id": campaign_id})
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch jobs: {resp.status_code} {resp.text}")
    
    # Fix: Check if response has "data" wrapper or direct access
    response_data = resp.json()
    jobs_data = response_data.get("data", {}).get("jobs") or response_data.get("jobs", [])
    print(f"[API] Fetched {len(jobs_data)} total jobs for campaign {campaign_id}")
    return jobs_data


def wait_for_jobs(token, campaign_id, job_type, expected_count=None, timeout=300, interval=2, start_time=None):
    print(f"[Polling] Starting to wait for {job_type} jobs (campaign {campaign_id})")
    if expected_count:
        print(f"[Polling] Expecting {expected_count} {job_type} job(s) to complete")
    else:
        print(f"[Polling] Waiting for any {job_type} job(s) to complete")
    
    waited = 0
    last_status_log = 0
    status_log_interval = 10  # Log status every 10 seconds
    
    while waited < timeout:
        jobs = fetch_campaign_jobs(token, campaign_id)
        target = [j for j in jobs if j["job_type"] == job_type]
        
        # Filter jobs to only include those created after start_time if provided
        # BUT don't filter ENRICH_LEAD jobs since they're always created as part of current campaign
        if start_time and job_type != "ENRICH_LEAD":
            from datetime import datetime
            target = [j for j in target if j.get("created_at") and j["created_at"] > start_time]
        
        # Log current status periodically
        if waited - last_status_log >= status_log_interval:
            print(f"[Polling] {waited}s elapsed - Found {len(target)} {job_type} job(s)")
            if target:
                status_counts = {}
                for job in target:
                    status = job["status"]
                    status_counts[status] = status_counts.get(status, 0) + 1
                status_summary = ", ".join(f"{status}: {count}" for status, count in status_counts.items())
                print(f"[Polling] Job status breakdown: {status_summary}")
            last_status_log = waited
        
        if expected_count and len(target) < expected_count:
            print(f"[Polling] Only found {len(target)}/{expected_count} {job_type} jobs, waiting...")
            time.sleep(interval)
            waited += interval
            continue

        if target and all(j["status"] in ("COMPLETED", "FAILED") for j in target):
            failed = [j for j in target if j["status"] == "FAILED"]
            if failed:
                print(f"[Polling] ERROR: {len(failed)} {job_type} job(s) failed!")
                for job in failed:
                    error_msg = job.get('error') or job.get('error_message', 'Unknown error')
                    print(f"[Polling] Failed job {job['id']}: {error_msg}")
                msgs = "; ".join(f.get('error') or f.get('error_message', 'Unknown error') for f in failed)
                raise AssertionError(f"{job_type} job(s) failed: {msgs}")
            
            print(f"[Polling] SUCCESS: All {len(target)} {job_type} job(s) completed after {waited}s")
            return target

        time.sleep(interval)
        waited += interval
    
    # Timeout reached - provide detailed status
    print(f"[Polling] TIMEOUT: {job_type} jobs not finished within {timeout}s")
    jobs = fetch_campaign_jobs(token, campaign_id)
    target = [j for j in jobs if j["job_type"] == job_type]
    if target:
        print(f"[Polling] Final status of {len(target)} {job_type} job(s):")
        for job in target:
            print(f"[Polling]   Job {job['id']}: {job['status']} - {job.get('error_message', 'No error message')}")
    else:
        print(f"[Polling] No {job_type} jobs found at timeout")
    
    raise TimeoutError(f"{job_type} jobs not finished within {timeout}s")


def get_all_leads(token, campaign_id):
    print(f"[API] Fetching all leads for campaign {campaign_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_BASE}/leads", headers=headers, params={"campaign_id": campaign_id})
    if resp.status_code != 200:
        raise Exception(f"Leads fetch failed: {resp.status_code} {resp.text}")
    
    # Fix: Check if response has "data" wrapper or direct access
    response_data = resp.json()
    leads_data = response_data.get("data", {}).get("leads") or response_data.get("leads", [])
    print(f"[API] Successfully retrieved {len(leads_data)} leads")
    return leads_data


# ---------------- Assertion helper ----------------

def assert_lead_enrichment(updated_lead, mock_lead, timeout):
    assert updated_lead.get("enrichment_results"), f"No enrichment_results for {updated_lead['email']} after {timeout}s"
    assert updated_lead.get("email_copy_gen_results"), f"No email_copy_gen_results for {updated_lead['email']} after {timeout}s"
    assert updated_lead.get("instantly_lead_record"), f"No instantly_lead_record for {updated_lead['email']} after {timeout}s"
    assert mock_lead is not None
    assert updated_lead["first_name"] == mock_lead["first_name"]
    assert updated_lead["last_name"] == mock_lead["last_name"]
    assert updated_lead["company"] == (mock_lead.get("organization", {}).get("name") or mock_lead.get("organization_name", ""))

def cleanup_test_data():
    """Clean up test data from database."""
    try:
        # Override DATABASE_URL for local connection
        import sqlalchemy
        from app.core.config import settings
        
        # Use local database with Docker port mapping
        db_url = f"postgresql://postgres:postgres@localhost:15432/fastapi_k8_proto"
        engine = sqlalchemy.create_engine(db_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        db = SessionLocal()
        try:
            # Delete test user and related data
            test_user = db.query(User).filter(User.email == TEST_EMAIL).first()
            if test_user:
                print(f"[Cleanup] Removing test user: {TEST_EMAIL}")
                db.delete(test_user)
                db.commit()
                print(f"[Cleanup] Test data cleaned up successfully")
        except Exception as e:
            print(f"[Cleanup] Error during cleanup: {e}")
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        print(f"[Cleanup] Could not connect to database for cleanup: {e}")

def main():
    from app.background_services.smoke_tests.mock_apify_client import MOCK_LEADS_DATA
    
    print("\n" + "="*60)
    print("🚀 STARTING CAMPAIGN FLOW TEST")
    print("="*60)
    
    try:
        print("\n📋 PHASE 1: Authentication & Setup")
        print("-" * 30)
        token, email = signup_and_login()
        organization_id = create_organization(token)
        campaign_id = create_campaign(token, organization_id=organization_id)
        
        print(f"\n🎯 PHASE 2: Campaign Execution")
        print("-" * 30)
        from datetime import datetime
        campaign_start_time = datetime.utcnow().isoformat()
        start_campaign(token, campaign_id)

        print(f"\n⏳ PHASE 3: Lead Fetching")
        print("-" * 30)
        print(f"[Phase] Waiting for FETCH_LEADS job to complete...")
        wait_for_jobs(token, campaign_id, "FETCH_LEADS", expected_count=1, timeout=120, start_time=campaign_start_time)

        print(f"\n📊 PHASE 4: Lead Data Verification")
        print("-" * 30)
        leads = get_all_leads(token, campaign_id)
        print(f"[Phase] Retrieved {len(leads)} leads from database")
        
        mock_emails = {lead["email"] for lead in MOCK_LEADS_DATA}
        db_emails = {lead["email"] for lead in leads}
        print(f"[Phase] Expected {len(mock_emails)} leads, found {len(db_emails)} leads")
        print(f"[Phase] Expected emails: {sorted(mock_emails)}")
        print(f"[Phase] Database emails: {sorted(db_emails)}")
        
        assert mock_emails == db_emails, f"Emails in DB: {db_emails}, expected: {mock_emails}"
        print(f"[Phase] ✓ Lead data verification passed!")

        print(f"\n⚡ PHASE 5: Lead Enrichment")
        print("-" * 30)
        print(f"[Phase] Waiting for {len(leads)} ENRICH_LEAD job(s) to complete...")
        wait_for_jobs(token, campaign_id, "ENRICH_LEAD", expected_count=len(leads), timeout=300)

        print(f"\n✅ PHASE 6: Enrichment Validation")
        print("-" * 30)
        validate_enrichment(leads, token)

        print("\n" + "="*60)
        print("🎉 CAMPAIGN FLOW TEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"✓ {len(leads)} leads fetched")
        print(f"✓ {len(leads)} leads enriched") 
        print(f"✓ {len(leads)} leads validated")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    finally:
        # Clean up test data
        cleanup_test_data()

if __name__ == "__main__":
    main() 