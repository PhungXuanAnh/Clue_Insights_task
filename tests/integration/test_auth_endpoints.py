"""
Integration tests for authentication endpoints.
"""
import json
import pytest

from app.models.user import User


def test_user_registration_success(client, db_session):
    """Test successful user registration."""
    # Prepare test data
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123'
    }
    
    # Send registration request
    response = client.post(
        '/api/auth/register',
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
        '/api/auth/register',
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
        '/api/auth/register',
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
        '/api/auth/register',
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
        '/api/auth/register',
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
        '/api/auth/register',
        data=json.dumps(user_data),
        content_type='application/json'
    )
    
    assert response.status_code == 409
    data = json.loads(response.data)
    assert 'Username or email already exists' in data['message'] 