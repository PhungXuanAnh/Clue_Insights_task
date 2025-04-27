"""
Development environment configuration module.
"""
from app.config.base_config import BaseConfig


class DevelopmentConfig(BaseConfig):
    """Development environment configuration class."""

    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries
    
    # Override any other settings for development
    DB_NAME = "subscription_dev_db"
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user:password@db:3306/subscription_dev_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False 