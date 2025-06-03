"""
Authentication and user management utilities for smoke tests.
"""

import requests
import random
import string
from app.core.config import settings

def random_email():
    """Generate a random email for test user."""
    return f"testuser_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}@hellacooltestingdomain.pizza"

def random_password():
    """Generate a random password that meets requirements."""
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

def signup_and_login(api_base=None):
    """
    Create a new test user and authenticate.
    
    Args:
        api_base: API base URL, defaults to settings-based URL
        
    Returns:
        tuple: (token, email) for authenticated user
    """
    if api_base is None:
        api_base = f"http://localhost:8000{settings.API_V1_STR}"
        
    email = random_email()
    password = random_password()
    signup_data = {
        "email": email,
        "password": password,
        "confirm_password": password
    }
    print(f"[Auth] Signing up test user: {email}")
    resp = requests.post(f"{api_base}/auth/signup", json=signup_data)
    if resp.status_code not in (200, 201):
        print(f"[Auth] Signup failed: {resp.status_code} {resp.text}")
        raise Exception("Signup failed")
    print(f"[Auth] Signing in test user: {email}")
    resp = requests.post(f"{api_base}/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        print(f"[Auth] Login failed: {resp.status_code} {resp.text}")
        raise Exception("Login failed")
    
    # Fix: Access token directly from response (no "data" wrapper)
    response_data = resp.json()
    token = response_data["token"]["access_token"]
    print(f"[Auth] Got token: {token[:8]}...")
    return token, email

def create_organization(token, api_base=None):
    """
    Create a test organization.
    
    Args:
        token: Authentication token
        api_base: API base URL, defaults to settings-based URL
        
    Returns:
        str: Organization ID
    """
    if api_base is None:
        api_base = f"http://localhost:8000{settings.API_V1_STR}"
        
    headers = {"Authorization": f"Bearer {token}"}
    org_data = {
        "name": "Test Org",
        "description": "A test organization for concurrent campaigns."
    }
    resp = requests.post(f"{api_base}/organizations", json=org_data, headers=headers)
    if resp.status_code != 201:
        print(f"[Org] Creation failed: {resp.status_code} {resp.text}")
        raise Exception("Organization creation failed")
    
    # Fix: Check if response has "data" wrapper or direct access
    response_data = resp.json()
    org_id = response_data.get("data", {}).get("id") or response_data.get("id")
    print(f"[Org] Created organization with id: {org_id}")
    return org_id 