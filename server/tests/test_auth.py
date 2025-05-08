"""
Tests for authentication endpoints (/auth/signup and /auth/login).
Tests are organized by endpoint and then by test case.
"""
import pytest
from flask import json
from server.models import User

# Signup Tests
def test_signup_success(client, test_user):
    """Test successful user registration."""
    response = client.post('/api/auth/signup', json=test_user)
    assert response.status_code == 201
    assert response.json['message'] == 'User registered successfully'
    
    # Verify user was created in database
    with client.application.app_context():
        user = User.query.filter_by(email=test_user['email']).first()
        assert user is not None
        assert user.email == test_user['email']

def test_signup_missing_fields(client):
    """Test signup with missing required fields."""
    # Missing email
    response = client.post('/api/auth/signup', json={
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })
    assert response.status_code == 400
    assert 'All fields are required' in response.json['error']

    # Missing password
    response = client.post('/api/auth/signup', json={
        'email': 'user@example.com',
        'confirm_password': 'SecurePass123!'
    })
    assert response.status_code == 400
    assert 'All fields are required' in response.json['error']

    # Missing confirm_password
    response = client.post('/api/auth/signup', json={
        'email': 'user@example.com',
        'password': 'SecurePass123!'
    })
    assert response.status_code == 400
    assert 'All fields are required' in response.json['error']

def test_signup_invalid_email(client, test_user):
    """Test signup with invalid email format."""
    test_user['email'] = 'invalid-email'
    response = client.post('/api/auth/signup', json=test_user)
    assert response.status_code == 400
    assert 'Invalid email format' in response.json['error']

def test_signup_password_mismatch(client, test_user):
    """Test password confirmation mismatch."""
    test_user['confirm_password'] = 'DifferentPass123!'
    response = client.post('/api/auth/signup', json=test_user)
    assert response.status_code == 400
    assert 'Passwords do not match' in response.json['error']

def test_signup_weak_password(client):
    """Test signup with weak passwords."""
    test_cases = [
        ('short', 'Password must be at least 8 characters long'),
        ('123456789!', 'Password must contain at least one letter'),
        ('NoSpecialChar1', 'Password must contain at least one special character'),
        ('NoNumber!', 'Password must contain at least one number'),
        ('12345678!', 'Password must contain at least one letter')
    ]
    
    for password, expected_error in test_cases:
        response = client.post('/api/auth/signup', json={
            'email': 'user@example.com',
            'password': password,
            'confirm_password': password
        })
        assert response.status_code == 400
        assert expected_error in response.json['error']

def test_signup_duplicate_email(client, test_user):
    """Test signup with existing email."""
    # First signup
    client.post('/api/auth/signup', json=test_user)
    
    # Try to signup again with same email
    response = client.post('/api/auth/signup', json=test_user)
    assert response.status_code == 400
    assert 'Email already registered' in response.json['error']

def test_signup_invalid_json(client):
    """Test signup with invalid JSON payload."""
    response = client.post('/api/auth/signup', 
        data='invalid json',
        content_type='application/json'
    )
    assert response.status_code == 400
    assert 'Invalid JSON payload' in response.json['error']

def test_signup_email_case_insensitive(client, test_user):
    """Test that email registration is case insensitive."""
    # Register with lowercase
    response = client.post('/api/auth/signup', json=test_user)
    assert response.status_code == 201

    # Try to register with uppercase
    test_user_upper = test_user.copy()
    test_user_upper['email'] = test_user['email'].upper()
    response = client.post('/api/auth/signup', json=test_user_upper)
    assert response.status_code == 400
    assert 'Email already registered' in response.json['error']

def test_signup_long_inputs(client):
    """Test signup with very long inputs."""
    # Test with very long email
    long_email = 'a' * 256 + '@example.com'
    response = client.post('/api/auth/signup', json={
        'email': long_email,
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })
    assert response.status_code == 400
    assert 'Email length exceeds maximum allowed' in response.json['error']

    # Test with very long password
    long_password = 'A' * 73 + '123!'  # bcrypt has 72-byte limit
    response = client.post('/api/auth/signup', json={
        'email': 'valid@example.com',
        'password': long_password,
        'confirm_password': long_password
    })
    assert response.status_code == 400
    assert 'Password length exceeds maximum allowed' in response.json['error']

# Login Tests
def test_login_success(client, test_user):
    """Test successful login."""
    # First create the user
    client.post('/api/auth/signup', json=test_user)
    
    # Try to login
    response = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']
    })
    assert response.status_code == 200
    assert 'token' in response.json
    assert response.json['message'] == 'Login successful'

def test_login_missing_fields(client):
    """Test login with missing required fields."""
    # Test missing email
    response = client.post('/api/auth/login', json={
        'password': 'TestPass123!'
    })
    assert response.status_code == 400
    assert 'Missing email or password' in response.json['error']

    # Test missing password
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com'
    })
    assert response.status_code == 400
    assert 'Missing email or password' in response.json['error']

def test_login_invalid_email(client):
    """Test login with invalid email format."""
    response = client.post('/api/auth/login', json={
        'email': 'notanemail',
        'password': 'SecurePass123!'
    })
    assert response.status_code == 400
    assert 'Invalid email format' in response.json['error']

def test_login_wrong_password(client, test_user):
    """Test login with wrong password."""
    # First create the user
    client.post('/api/auth/signup', json=test_user)
    
    # Try to login with wrong password
    response = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': 'WrongPass123!'
    })
    assert response.status_code == 401
    assert 'Invalid email or password' in response.json['error']

def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    response = client.post('/api/auth/login', json={
        'email': 'nonexistent@example.com',
        'password': 'SomePass123!'
    })
    assert response.status_code == 401
    assert 'Invalid email or password' in response.json['error']

def test_login_case_insensitive_email(client, test_user):
    """Test that login is case insensitive for email."""
    # First register the user
    client.post('/api/auth/signup', json=test_user)
    
    # Try to login with uppercase email
    response = client.post('/api/auth/login', json={
        'email': test_user['email'].upper(),
        'password': test_user['password']
    })
    assert response.status_code == 200
    assert 'token' in response.json

def test_login_invalid_json(client):
    """Test login with invalid JSON payload."""
    response = client.post('/api/auth/login',
        data='invalid json',
        content_type='application/json'
    )
    assert response.status_code == 400
    assert 'Invalid JSON payload' in response.json['error']

def test_login_account_lockout(client, test_user):
    """Test account lockout after multiple failed attempts."""
    # First create the user
    client.post('/api/auth/signup', json=test_user)
    
    # Try to login with wrong password multiple times
    for _ in range(5):  # Assuming 5 is the max attempts
        response = client.post('/api/auth/login', json={
            'email': test_user['email'],
            'password': 'WrongPass123!'
        })
    
    # Verify account is locked
    response = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']  # Correct password
    })
    assert response.status_code == 403
    assert 'account is locked' in response.json['error'].lower() 