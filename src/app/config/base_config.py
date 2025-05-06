"""
Base configuration module with common settings.
"""
import os


class BaseConfig:
    """Base configuration class with common settings."""

    # Flask settings
    SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-key-not-for-production")
    DEBUG = False
    TESTING = False

    # Database settings
    DB_ENGINE = os.getenv("DB_ENGINE", "mysql")
    DB_USER = os.getenv("DB_USER", "user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "subscription_db")
    
    # Use pymysql if DB_ENGINE doesn't specify dialect
    if DB_ENGINE == "mysql" and not "pymysql" in DB_ENGINE and not "mysqlclient" in DB_ENGINE:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        SQLALCHEMY_DATABASE_URI = f"{DB_ENGINE}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT settings
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-jwt-key-not-for-production")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 604800))  # 7 days

    # API settings
    API_TITLE = "Subscription Management API"
    API_VERSION = "1.0"
    API_DESCRIPTION = "A RESTful API for managing user subscriptions with optimized SQL queries"
    API_PREFIX = "/api" 