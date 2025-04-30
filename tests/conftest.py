"""
Pytest configuration and fixtures.
"""
import os
import signal
import sys
import time

import pytest
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app


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
        from app import db
        
        max_attempts = 5
        attempt = 0
        connection_successful = False
        
        while not connection_successful and attempt < max_attempts:
            try:
                db.session.execute(text('SELECT 1'))
                connection_successful = True
            except Exception as e:
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(3)
                else:
                    raise

        # Create all database tables
        db.create_all()
        yield app
        # NOTE: If any test opens a DB connection (even just a read),
        # but the DB is unavailable or the connection is lost by teardown, db.drop_all() can hang indefinitely. 
        # Wrapping in a timeout and try/except ensures teardown does not block the test process.
        # for example:
        # | Test Name                        | DB Write? | DB Query? | Hangs on Teardown? |
        # |-----------------------------------|-----------|-----------|--------------------|
        # | test_user_login_nonexistent_user  | No        | Yes       | Yes                |
        # | test_user_login_missing_fields    | No        | No        | No                 |
        # | test_user_registration_success    | Yes       | Yes       | No                 |
        # For fixing this issue, we can use the autouse=True option in the db_session fixture.
        # This ensure that connection is closed after the test is run.
        def handler(signum, frame):
            raise TimeoutError('db.drop_all() timed out')
        try:
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(10)  # 10 second timeout
            try:
                db.drop_all()
            except Exception as e:
                print(f"Error during db.drop_all(): {e}", file=sys.stderr)
            finally:
                signal.alarm(0)
        except Exception as e:
            print(f"Teardown error or signal not available: {e}", file=sys.stderr)

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


# NOTE: to fix the issue of the db connection not being closed after the test is run,
# this issue cause hang on teardown of app fixture while calling db.drop_all(),
# we can use the autouse=True option in the db_session fixture.
@pytest.fixture(scope="function", autouse=True)
def db_session(app):
    """
    Create a fresh database session for a test.
    
    Args:
        app: The Flask application fixture.
    
    Returns:
        SQLAlchemy session: A database session for testing.
    """
    with app.app_context():
        from app import db
        
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Create a session using sessionmaker and scoped_session
        session_factory = sessionmaker(bind=connection)
        session = scoped_session(session_factory)
        
        # Override the default session with our test session
        old_session = db.session
        db.session = session
        yield session
        # Roll back the transaction and restore the original session
        db.session = old_session
        session.remove()  # Remove session first
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def db(app):
    """
    Fixture for the SQLAlchemy database object.
    
    Args:
        app: The Flask application fixture.
    
    Returns:
        SQLAlchemy db: The database object for testing.
    """
    from app import db as _db
    return _db