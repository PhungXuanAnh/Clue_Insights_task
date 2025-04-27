"""
Integration tests for the API.
"""
import json

import pytest

from app import create_app


def test_health_endpoint():
    """Test the health endpoint returns a 200 response."""
    app = create_app('testing')
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'healthy'
        assert data['environment'] == 'testing'


def test_api_docs_endpoint():
    """Test the API docs endpoint returns a 200 response."""
    app = create_app('testing')
    with app.test_client() as client:
        response = client.get('/api/docs')
        assert response.status_code == 200
        assert b'Swagger' in response.data 