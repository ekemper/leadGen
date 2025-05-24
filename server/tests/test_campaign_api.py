import pytest
from datetime import datetime, timedelta

from server.models.job import Job
from server.models.campaign_status import CampaignStatus
from server.config.database import db

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def campaign_payload():
    """Return a valid payload for creating a campaign via the API."""
    return {
        "name": "API Test Campaign",
        "description": "This campaign is created by tests",
        "fileName": "input-file.csv",
        "totalRecords": 25,
        "url": "https://app.apollo.io/#/some-search",
        "organization_id": "org-test"
    }

# ---------------------------------------------------------------------------
# Campaign creation & listing
# ---------------------------------------------------------------------------

def test_create_campaign_success(client, auth_headers, campaign_payload):
    resp = client.post("/api/campaigns", json=campaign_payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json["data"]
    assert data["name"] == campaign_payload["name"]
    assert data["status"] == CampaignStatus.CREATED
    for fld in ("fileName", "totalRecords", "url"):
        assert data[fld] == campaign_payload[fld]


def test_create_campaign_validation_error(client, auth_headers):
    bad_payload = {"name": "Missing", "fileName": "file.csv", "url": "https://app.apollo.io"}
    resp = client.post("/api/campaigns", json=bad_payload, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json["status"] == "error"


def test_list_campaigns(client, auth_headers, campaign_payload):
    for i in range(2):
        payload = {**campaign_payload, "name": f"Campaign {i}"}
        client.post("/api/campaigns", json=payload, headers=auth_headers)
    resp = client.get("/api/campaigns", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json["data"]["campaigns"]) >= 2

# ---------------------------------------------------------------------------
# Retrieve single campaign
# ---------------------------------------------------------------------------

def test_get_campaign_by_id(client, auth_headers, campaign_payload):
    create = client.post("/api/campaigns", json=campaign_payload, headers=auth_headers)
    cid = create.json["data"]["id"]
    resp = client.get(f"/api/campaigns/{cid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json["data"]["id"] == cid

# ---------------------------------------------------------------------------
# Start campaign flow
# ---------------------------------------------------------------------------

def test_start_campaign_flow(client, auth_headers, campaign_payload):
    create = client.post("/api/campaigns", json=campaign_payload, headers=auth_headers)
    cid = create.json["data"]["id"]
    start = client.post(f"/api/campaigns/{cid}/start", headers=auth_headers)
    assert start.status_code == 200
    assert start.json["data"]["status"] == CampaignStatus.FETCHING_LEADS
    with client.application.app_context():
        jobs = Job.query.filter_by(campaign_id=cid, job_type="FETCH_LEADS").count()
        assert jobs == 1


def test_start_campaign_duplicate(client, auth_headers, campaign_payload):
    c = client.post("/api/campaigns", json=campaign_payload, headers=auth_headers)
    cid = c.json["data"]["id"]
    client.post(f"/api/campaigns/{cid}/start", headers=auth_headers)
    dup = client.post(f"/api/campaigns/{cid}/start", headers=auth_headers)
    assert dup.status_code == 400

# ---------------------------------------------------------------------------
# PATCH campaign
# ---------------------------------------------------------------------------

def test_patch_campaign(client, auth_headers, campaign_payload):
    c = client.post("/api/campaigns", json=campaign_payload, headers=auth_headers)
    cid = c.json["data"]["id"]
    patch = client.patch(f"/api/campaigns/{cid}", json={"description": "New desc"}, headers=auth_headers)
    assert patch.status_code == 200
    assert patch.json["data"]["description"] == "New desc"

# ---------------------------------------------------------------------------
# Cleanup jobs endpoint
# ---------------------------------------------------------------------------

def test_cleanup_old_jobs(client, auth_headers, campaign_payload):
    c = client.post("/api/campaigns", json=campaign_payload, headers=auth_headers)
    cid = c.json["data"]["id"]
    with client.application.app_context():
        old_job = Job(id="old-job", campaign_id=cid, job_type="FETCH_LEADS", status="completed", result={}, created_at=datetime.utcnow() - timedelta(days=10))
        db.session.add(old_job)
        db.session.commit()
    resp = client.post(f"/api/campaigns/{cid}/cleanup", json={"days": 7}, headers=auth_headers)
    assert resp.status_code == 200
    with client.application.app_context():
        remaining = Job.query.filter_by(campaign_id=cid).count()
        assert remaining == 0

# ---------------------------------------------------------------------------
# Additional creation edge-cases (security / length)
# ---------------------------------------------------------------------------

def test_create_campaign_special_characters(client, auth_headers, campaign_payload):
    payload = {**campaign_payload, "name": "!@#$%^&*()_+-=[]{}|;:,.<>?/~`\"'\\"}
    r = client.post("/api/campaigns", json=payload, headers=auth_headers)
    assert r.status_code == 201
    assert r.json["data"]["name"] == payload["name"]


def test_create_campaign_xss(client, auth_headers, campaign_payload):
    payload = {
        **campaign_payload,
        "name": "<script>alert(\"XSS\")</script>Campaign",
        "description": "<img src=x onerror=alert('XSS')>"
    }
    r = client.post("/api/campaigns", json=payload, headers=auth_headers)
    assert r.status_code == 201
    assert r.json["data"]["name"] == payload["name"]
    assert r.json["data"]["description"] == payload["description"]


def test_create_campaign_long_description(client, auth_headers, campaign_payload):
    payload = {**campaign_payload, "description": "x" * 10000}
    r = client.post("/api/campaigns", json=payload, headers=auth_headers)
    assert r.status_code == 201
    assert len(r.json["data"]["description"]) == 10000
