"""
Test configuration module.
"""
import pytest

from app import create_app
from app.config.development_config import DevelopmentConfig
from app.config.production_config import ProductionConfig
from app.config.testing_config import TestingConfig


def test_development_config():
    """Test development configuration."""
    app = create_app('development')
    assert app.config['DEBUG'] is True
    assert app.config['TESTING'] is False
    assert 'subscription_dev_db' in app.config['SQLALCHEMY_DATABASE_URI']


def test_testing_config():
    """Test testing configuration."""
    app = create_app('testing')
    assert app.config['DEBUG'] is True
    assert app.config['TESTING'] is True
    assert 'subscription_test_db' in app.config['SQLALCHEMY_DATABASE_URI']


def test_production_config():
    """Test production configuration."""
    app = create_app('production')
    assert app.config['DEBUG'] is False
    assert app.config['TESTING'] is False 