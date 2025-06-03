import pytest

from tests.helpers.auth_helpers import AuthHelpers


def test_complete_user_workflow(client, db_session):
    """Test complete user workflow from signup to using protected endpoints."""
    
    # 1. User signs up
    signup_response = client.post("/api/v1/auth/signup", json={
        "email": "integration@hellacooltestingdomain.pizza",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!"
    })
    assert signup_response.status_code == 201
    
    # 2. User logs in
    login_response = client.post("/api/v1/auth/login", json={
        "email": "integration@hellacooltestingdomain.pizza",
        "password": "TestPass123!"
    })
    assert login_response.status_code == 200
    token = login_response.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. User accesses protected endpoint
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "integration@hellacooltestingdomain.pizza"
    
    # 4. User creates organization
    org_response = client.post("/api/v1/organizations/", 
        headers=headers,
        json={
            "name": "Integration Test Org",
            "description": "Created during integration test"
        }
    )
    assert org_response.status_code == 201
    org_response_data = org_response.json()
    
    # Check if organization endpoint uses structured response
    if "data" in org_response_data:
        org_id = org_response_data["data"]["id"]
    else:
        org_id = org_response_data["id"]
    
    # 5. User creates campaign
    campaign_response = client.post("/api/v1/campaigns/",
        headers=headers,
        json={
            "name": "Integration Test Campaign",
            "description": "Created during integration test",
            "fileName": "test.csv",
            "totalRecords": 10,
            "url": "https://example.com",
            "organization_id": org_id
        }
    )
    assert campaign_response.status_code == 201
    campaign_response_data = campaign_response.json()
    
    # Check structured response format
    assert "status" in campaign_response_data
    assert "data" in campaign_response_data
    assert campaign_response_data["status"] == "success"
    
    campaign_id = campaign_response_data["data"]["id"]
    
    # 6. User lists campaigns (should include our campaign)
    campaigns_response = client.get("/api/v1/campaigns/", headers=headers)
    assert campaigns_response.status_code == 200
    campaigns_response_data = campaigns_response.json()
    
    # Check structured response format
    assert "status" in campaigns_response_data
    assert "data" in campaigns_response_data
    assert campaigns_response_data["status"] == "success"
    
    campaigns = campaigns_response_data["data"]["campaigns"]
    assert len(campaigns) == 1
    assert campaigns[0]["id"] == campaign_id
    
    # 7. Verify database state
    from app.models.user import User
    from app.models.organization import Organization
    from app.models.campaign import Campaign
    
    user = db_session.query(User).filter(User.email == "integration@hellacooltestingdomain.pizza").first()
    assert user is not None
    
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    assert org is not None
    assert org.name == "Integration Test Org"
    
    campaign = db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert campaign is not None
    assert campaign.name == "Integration Test Campaign"
    assert campaign.organization_id == org_id


def test_authentication_edge_cases(client, db_session):
    """Test various authentication edge cases."""
    
    # Test accessing protected endpoint without auth
    response = client.get("/api/v1/campaigns/")
    assert response.status_code == 401
    
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/v1/campaigns/", headers=headers)
    assert response.status_code == 401
    
    # Test with malformed auth header
    headers = {"Authorization": "invalid_format"}
    response = client.get("/api/v1/campaigns/", headers=headers)
    assert response.status_code == 401
    
    # Test public endpoints still work
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_multi_user_isolation(client, db_session):
    """Test that multiple users can work independently."""
    
    # Create first user
    user1_signup = client.post("/api/v1/auth/signup", json={
        "email": "user1@hellacooltestingdomain.pizza",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!"
    })
    assert user1_signup.status_code == 201
    
    user1_login = client.post("/api/v1/auth/login", json={
        "email": "user1@hellacooltestingdomain.pizza",
        "password": "TestPass123!"
    })
    assert user1_login.status_code == 200
    user1_token = user1_login.json()["token"]["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}
    
    # Create second user
    user2_signup = client.post("/api/v1/auth/signup", json={
        "email": "user2@hellacooltestingdomain.pizza",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!"
    })
    assert user2_signup.status_code == 201
    
    user2_login = client.post("/api/v1/auth/login", json={
        "email": "user2@hellacooltestingdomain.pizza",
        "password": "TestPass123!"
    })
    assert user2_login.status_code == 200
    user2_token = user2_login.json()["token"]["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}
    
    # Both users can access their own data
    user1_me = client.get("/api/v1/auth/me", headers=user1_headers)
    assert user1_me.status_code == 200
    assert user1_me.json()["email"] == "user1@hellacooltestingdomain.pizza"
    
    user2_me = client.get("/api/v1/auth/me", headers=user2_headers)
    assert user2_me.status_code == 200
    assert user2_me.json()["email"] == "user2@hellacooltestingdomain.pizza"
    
    # Both users can create organizations
    user1_org = client.post("/api/v1/organizations/", 
        headers=user1_headers,
        json={"name": "User 1 Org", "description": "User 1's organization"}
    )
    assert user1_org.status_code == 201
    
    user2_org = client.post("/api/v1/organizations/", 
        headers=user2_headers,
        json={"name": "User 2 Org", "description": "User 2's organization"}
    )
    assert user2_org.status_code == 201
    
    # Verify both organizations exist in database
    from app.models.organization import Organization
    orgs = db_session.query(Organization).all()
    assert len(orgs) == 2
    org_names = {org.name for org in orgs}
    assert "User 1 Org" in org_names
    assert "User 2 Org" in org_names


def test_error_handling_with_auth(client, db_session):
    """Test error handling in authenticated endpoints."""
    
    # Create authenticated user
    user, token, headers = AuthHelpers.create_authenticated_user(db_session)
    
    # Test validation errors with auth
    response = client.post("/api/v1/campaigns/", 
        headers=headers,
        json={
            "name": "",  # Invalid empty name
            "description": "Test",
            "fileName": "test.csv",
            "totalRecords": -1,  # Invalid negative number
            "url": "invalid-url",
            "organization_id": "invalid-uuid"
        }
    )
    assert response.status_code == 422  # Validation error
    
    # Test not found errors with auth
    response = client.get("/api/v1/campaigns/non-existent-id", headers=headers)
    assert response.status_code == 404
    
    # Test accessing non-existent organization
    response = client.get("/api/v1/organizations/non-existent-id", headers=headers)
    assert response.status_code == 404 