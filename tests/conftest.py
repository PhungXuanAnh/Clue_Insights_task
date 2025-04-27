"""
Pytest configuration and fixtures.
"""
import os

import pytest
from dotenv import load_dotenv
from flask import Flask
from flask.testing import FlaskClient

from app import create_app, db


@pytest.fixture(scope="session")
def app():
    """
    Create a Flask application configured for testing.
    
    Returns:
        Flask: The Flask application instance.
    """
    # Load test environment variables
    load_dotenv(".env.testing", override=True)

    # Set the Flask environment to testing
    os.environ["FLASK_ENV"] = "testing"
    
    # Create the Flask app using the factory
    app = create_app()
    
    # Use the app context for the duration of the test
    with app.app_context():
        # Create all database tables
        db.create_all()
        
        yield app
        
        # Clean up: drop all tables
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """
    Create a test client for the Flask application.
    
    Args:
        app: The Flask application fixture.
        
    Returns:
        FlaskClient: A test client for the Flask application.
    """
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    """
    Create a fresh database session for a test.
    
    Args:
        app: The Flask application fixture.
    
    Returns:
        SQLAlchemy session: A database session for testing.
    """
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Create a session with the connection
        session = db.create_scoped_session(
            options={"bind": connection, "binds": {}}
        )
        
        db.session = session
        
        yield session
        
        # Roll back the transaction
        transaction.rollback()
        connection.close()
        session.remove() 