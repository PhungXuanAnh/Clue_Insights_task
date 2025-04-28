"""
Testing environment configuration module.
"""
from app.config.base_config import BaseConfig


class TestingConfig(BaseConfig):
    """Testing environment configuration class."""

    TESTING = True
    DEBUG = True
    
    # Use a separate database for testing
    DB_NAME = "subscription_test_db"
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user:password@test-db:3306/subscription_test_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Disable CSRF protection in testing
    WTF_CSRF_ENABLED = False
    
    # Use faster hashing for tests
    BCRYPT_LOG_ROUNDS = 4
    
    # JWT settings for testing
    JWT_ACCESS_TOKEN_EXPIRES = 300  # 5 minutes
    JWT_REFRESH_TOKEN_EXPIRES = 1800  # 30 minutes
    JWT_ERROR_MESSAGE_KEY = "message"
    JWT_BLACKLIST_ENABLED = False
    # Use a predictable key for testing
    JWT_SECRET_KEY = "test-jwt-secret-key-for-testing-only" 