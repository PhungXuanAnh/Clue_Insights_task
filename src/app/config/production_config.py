"""
Production environment configuration module.
"""
import os

from app.config.base_config import BaseConfig


class ProductionConfig(BaseConfig):
    """Production environment configuration class."""

    # NOTE: Production should never run in debug mode
    DEBUG = False
    
    # Use environment variables with no defaults for production
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    # JWT settings for production - more secure settings
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))  # 1 hour default
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 604800))  # 7 days default
    JWT_ERROR_MESSAGE_KEY = "message"
    JWT_BLACKLIST_ENABLED = True  # Enable blacklist in production
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]  # Check both token types
    JWT_COOKIE_SECURE = True  # Only send cookies over HTTPS
    JWT_COOKIE_CSRF_PROTECT = True  # Enable CSRF protection
    
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