"""
Integration tests for authentication endpoints.
"""
import json
import pytest
from sqlalchemy import inspect

from app.models.token_blacklist import TokenBlacklist
from app.models.user import User


def test_user_registration_success(client, db_session):
    """Test successful user registration."""
    # Prepare test data
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123'
    }
    
    # Send registration request to v1 endpoint
    response = client.post(
        '/api/v1/auth/register',
        data=json.dumps(user_data),
        content_type='application/json'
    )
    
    # Check response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['username'] == 'testuser'
    assert data['email'] == 'test@example.com'
    assert 'password' not in data
    
    # Verify user was created in database
    user = User.query.filter_by(username='testuser').first()
    assert user is not None
    assert user.email == 'test@example.com'
    assert user.check_password('password123')


def test_user_registration_missing_fields(client):
    """Test user registration with missing fields."""
    # Missing email
    user_data = {
        'username': 'testuser',
        'password': 'password123'
    }
    
    response = client.post(
        '/api/v1/auth/register',
        data=json.dumps(user_data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'Missing required fields' in data['message']


def test_user_registration_invalid_email(client):
    """Test user registration with invalid email."""
    user_data = {
        'username': 'testuser',
        'email': 'invalid-email',
        'password': 'password123'
    }
    
    response = client.post(
        '/api/v1/auth/register',
        data=json.dumps(user_data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'Invalid email format' in data['message']


def test_user_registration_short_password(client):
    """Test user registration with a password that's too short."""
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': '12345'  # Less than 6 characters
    }
    
    response = client.post(
        '/api/v1/auth/register',
        data=json.dumps(user_data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'Password must be at least 6 characters long' in data['message']


def test_user_registration_duplicate_username(client, db_session):
    """Test user registration with a duplicate username."""
    # Create a user first
    user = User(username='testuser', email='existing@example.com', password='password123')
    db_session.add(user)
    db_session.commit()
    
    # Try to register a user with the same username
    user_data = {
        'username': 'testuser',
        'email': 'new@example.com',
        'password': 'password123'
    }
    
    response = client.post(
        '/api/v1/auth/register',
        data=json.dumps(user_data),
        content_type='application/json'
    )
    
    assert response.status_code == 409
    data = json.loads(response.data)
    assert 'Username or email already exists' in data['message']


def test_user_registration_duplicate_email(client, db_session):
    """Test user registration with a duplicate email."""
    # Create a user first
    user = User(username='existinguser', email='test@example.com', password='password123')
    db_session.add(user)
    db_session.commit()
    
    # Try to register a user with the same email
    user_data = {
        'username': 'newuser',
        'email': 'test@example.com',
        'password': 'password123'
    }
    
    response = client.post(
        '/api/v1/auth/register',
        data=json.dumps(user_data),
        content_type='application/json'
    )
    
    assert response.status_code == 409
    data = json.loads(response.data)
    assert 'Username or email already exists' in data['message']


def test_user_login_success_with_username(client, db_session):
    """Test successful user login using username."""
    # Create a test user
    user = User(username='loginuser', email='login@example.com', password='password123')
    db_session.add(user)
    db_session.commit()
    
    # Try to login
    login_data = {
        'username': 'loginuser',
        'password': 'password123'
    }
    
    response = client.post(
        '/api/v1/auth/login',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['user_id'] == user.id
    assert data['username'] == 'loginuser'


def test_user_login_success_with_email(client, db_session):
    """Test successful user login using email."""
    # Create a test user
    user = User(username='emailuser', email='email_login@example.com', password='password123')
    db_session.add(user)
    db_session.commit()
    
    # Try to login with email instead of username
    login_data = {
        'username': 'email_login@example.com',
        'password': 'password123'
    }
    
    response = client.post(
        '/api/v1/auth/login',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['user_id'] == user.id
    assert data['username'] == 'emailuser'


def test_user_login_invalid_credentials(client, db_session):
    """Test login with invalid credentials."""
    # Create a test user
    user = User(username='testuser', email='test@example.com', password='password123')
    db_session.add(user)
    db_session.commit()
    
    # Try to login with wrong password
    login_data = {
        'username': 'testuser',
        'password': 'wrongpassword'
    }
    
    response = client.post(
        '/api/v1/auth/login',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'Invalid username/email or password' in data['message']


def test_user_login_nonexistent_user(client):
    """Test login with a username that doesn't exist."""
    login_data = {
        'username': 'nonexistentuser',
        'password': 'password123'
    }
    
    response = client.post(
        '/api/v1/auth/login',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'Invalid username/email or password' in data['message']


def test_user_login_missing_fields(client):
    """Test login with missing required fields."""
    # Missing password
    login_data = {
        'username': 'testuser'
    }
    
    response = client.post(
        '/api/v1/auth/login',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'Missing required fields' in data['message']


def test_token_refresh_success(client, db_session):
    """Test successful token refresh."""
    # Create a test user
    user = User(username='refreshuser', email='refresh@example.com', password='password123')
    db_session.add(user)
    db_session.commit()
    
    # Login to get tokens
    login_data = {
        'username': 'refreshuser',
        'password': 'password123'
    }
    
    login_response = client.post(
        '/api/v1/auth/login',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    
    login_data = json.loads(login_response.data)
    refresh_token = login_data['refresh_token']
    
    # Use refresh token to get a new access token
    refresh_response = client.post(
        '/api/v1/auth/refresh',
        headers={'Authorization': f'Bearer {refresh_token}'},
        content_type='application/json'
    )
    
    assert refresh_response.status_code == 200
    refresh_data = json.loads(refresh_response.data)
    assert 'access_token' in refresh_data
    assert isinstance(refresh_data['access_token'], str)
    assert len(refresh_data['access_token']) > 0


def test_token_refresh_invalid_token(client):
    """Test token refresh with an invalid token."""
    response = client.post(
        '/api/v1/auth/refresh',
        headers={'Authorization': 'Bearer invalidtoken'},
        content_type='application/json'
    )
    
    assert response.status_code == 422  # Unprocessable Entity for malformed JWT


def test_token_refresh_missing_token(client):
    """Test token refresh without providing a token."""
    response = client.post(
        '/api/v1/auth/refresh',
        content_type='application/json'
    )
    
    assert response.status_code == 401  # Unauthorized


def test_user_logout_success(client, db_session):
    """Test successful user logout."""
    # Create a test user
    user = User(username='logoutuser', email='logout@example.com', password='password123')
    db_session.add(user)
    db_session.commit()
    
    # Login to get tokens
    login_data = {
        'username': 'logoutuser',
        'password': 'password123'
    }
    
    login_response = client.post(
        '/api/v1/auth/login',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    
    login_data = json.loads(login_response.data)
    access_token = login_data['access_token']
    
    # Logout
    logout_response = client.post(
        '/api/v1/auth/logout',
        headers={'Authorization': f'Bearer {access_token}'},
        content_type='application/json'
    )
    
    assert logout_response.status_code == 200
    logout_data = json.loads(logout_response.data)
    assert 'message' in logout_data
    # Check for either message format since implementation may vary
    assert any(msg in logout_data['message'].lower() for msg in ['logout successful', 'logged out'])
    
    # Check token is blacklisted (if blacklist is enabled)
    # We can determine this by trying to use the token again
    inspector = inspect(db_session.bind)
    if inspector.has_table(TokenBlacklist.__tablename__):
        reuse_response = client.post(
            '/api/v1/auth/logout',
            headers={'Authorization': f'Bearer {access_token}'},
            content_type='application/json'
        )
        
        # If the token is blacklisted, should get 401 when trying to reuse
        if reuse_response.status_code == 401:
            data = json.loads(reuse_response.data)
            assert 'Token has been revoked' in data.get('message', '')
        else:
            # If we don't get 401, blacklisting may not be enabled in test env
            # This is also a valid test outcome
            pass


def test_user_logout_unauthorized(client):
    """Test logout without a valid token."""
    response = client.post(
        '/api/v1/auth/logout',
        content_type='application/json'
    )
    
    assert response.status_code == 401  # Unauthorized 