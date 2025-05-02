"""
Development environment configuration module.
"""
from app.config.base_config import BaseConfig


class DevelopmentConfig(BaseConfig):
    """Development environment configuration class."""

    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries
    SQLALCHEMY_RECORD_QUERIES = True  # Enable query recording for Flask-DebugToolbar
    
    # Override any other settings for development
    DB_NAME = "subscription_dev_db"
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user:password@db:3306/subscription_dev_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT settings for development
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours for easier development
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days
    JWT_ERROR_MESSAGE_KEY = "message"
    JWT_BLACKLIST_ENABLED = False  # No blacklist in development for simplicity 