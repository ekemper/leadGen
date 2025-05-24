import os
import sys
# Ensure project root is in sys.path for 'server' imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Enable the Apollo mock but leave Perplexity live
os.environ["USE_APIFY_CLIENT_MOCK"] = "true"  # keep Apollo mocked
import requests
import time
import random
import string
from server.models.user import User
from server.config.database import db
from flask import Flask

API_BASE = "http://localhost:5001/api"

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
    token = resp.json()["data"]["token"]
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

# After running enrichment jobs synchronously, validate each lead once.

def validate_enrichment(leads, token):
    headers = {"Authorization": f"Bearer {token}"}
    from server.background_services.mock_apify_client import MOCK_LEADS_DATA
    for lead in leads:
        resp = requests.get(f"{API_BASE}/leads/{lead['id']}", headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Lead fetch failed for {lead['id']}: {resp.status_code} {resp.text}")
        updated_lead = resp.json()["data"]
        mock_lead = next((l for l in MOCK_LEADS_DATA if l["email"] == lead["email"]), None)
        assert_lead_enrichment(updated_lead, mock_lead, timeout=60)
        print(f"[Enrichment] Lead {lead['email']} enrichment validated.")

# ---------------- Polling utilities ----------------

def fetch_campaign_jobs(token, campaign_id):
    """Return list of jobs for the given campaign via API."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_BASE}/jobs", headers=headers, params={"campaign_id": campaign_id})
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch jobs: {resp.status_code} {resp.text}")
    return resp.json()["data"]["jobs"]


def wait_for_jobs(token, campaign_id, job_type, expected_count=None, timeout=300, interval=2):
    waited = 0
    while waited < timeout:
        jobs = fetch_campaign_jobs(token, campaign_id)
        target = [j for j in jobs if j["job_type"] == job_type]
        if expected_count and len(target) < expected_count:
            time.sleep(interval)
            waited += interval
            continue

        if target and all(j["status"] in ("COMPLETED", "FAILED") for j in target):
            failed = [j for j in target if j["status"] == "FAILED"]
            if failed:
                msgs = "; ".join(f["error_message"] or "Unknown error" for f in failed)
                raise AssertionError(f"{job_type} job(s) failed: {msgs}")
            return target

        time.sleep(interval)
        waited += interval
    raise TimeoutError(f"{job_type} jobs not finished within {timeout}s")


def get_all_leads(token, campaign_id):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_BASE}/leads", headers=headers, params={"campaign_id": campaign_id})
    if resp.status_code != 200:
        raise Exception(f"Leads fetch failed: {resp.status_code} {resp.text}")
    return resp.json()["data"]["leads"]


# ---------------- Assertion helper ----------------

def assert_lead_enrichment(updated_lead, mock_lead, timeout):
    assert updated_lead.get("enrichment_results"), f"No enrichment_results for {updated_lead['email']} after {timeout}s"
    assert updated_lead.get("email_copy_gen_results"), f"No email_copy_gen_results for {updated_lead['email']} after {timeout}s"
    assert updated_lead.get("instantly_lead_record"), f"No instantly_lead_record for {updated_lead['email']} after {timeout}s"
    assert mock_lead is not None
    assert updated_lead["first_name"] == mock_lead["first_name"]
    assert updated_lead["last_name"] == mock_lead["last_name"]
    assert updated_lead["company"] == (mock_lead.get("organization", {}).get("name") or mock_lead.get("organization_name", ""))

def main():
    from server.background_services.mock_apify_client import MOCK_LEADS_DATA
    app = Flask(__name__)
    app.config.from_object('server.config.settings')
    # Ensure app context for db cleanup
    with app.app_context():
        token = None
        email = TEST_EMAIL
        # try:
        token, email = signup_and_login()
        organization_id = create_organization(token)
        campaign_id = create_campaign(token, organization_id=organization_id)
        start_campaign(token, campaign_id)

        # ----- Wait for fetch_leads to finish -----
        wait_for_jobs(token, campaign_id, "FETCH_LEADS", expected_count=1, timeout=120)

        leads = get_all_leads(token, campaign_id)
        mock_emails = {lead["email"] for lead in MOCK_LEADS_DATA}
        db_emails = {lead["email"] for lead in leads}
        assert mock_emails == db_emails, f"Emails in DB: {db_emails}, expected: {mock_emails}"

        # ----- Wait for all enrichment jobs -----
        wait_for_jobs(token, campaign_id, "ENRICH_LEAD", expected_count=len(leads), timeout=300)

        validate_enrichment(leads, token)

        print("\n[Success] All leads ingested and enriched successfully!")
        # finally:
            # Cleanup: delete the test user
            # user = User.query.filter_by(email=email).first()
            # if user:
            #     db.session.delete(user)
            #     db.session.commit()
            #     print(f"[Cleanup] Deleted test user: {email}")

if __name__ == "__main__":
    main() 