"""
Production environment configuration module.
"""
import os

from app.config.base_config import BaseConfig


class ProductionConfig(BaseConfig):
    """Production environment configuration class."""

    # Production should never run in debug mode
    DEBUG = False
    
    # Use environment variables with no defaults for production
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    
    # Database settings from environment with no defaults
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    
    # Build database URI - default to pymysql dialect
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Production usually doesn't need SQL echo
    SQLALCHEMY_ECHO = False
    
    # More secure session cookie settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True 