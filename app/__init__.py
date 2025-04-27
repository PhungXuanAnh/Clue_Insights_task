"""
Subscription Management API Application Factory.
"""
import importlib
import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_restx import Api
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()

def create_app(config_name=None):
    """
    Application Factory Pattern implementation.

    Args:
        config_name: Configuration name to use (development, testing, production).

    Returns:
        Flask application instance.
    """
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Configure the app
    app_config = os.getenv("FLASK_ENV", "development")
    if config_name:
        app_config = config_name
    
    # Print debug information
    print(f"Using configuration: {app_config}")
    
    try:
        # Map config_name to the proper module and class
        config_mapping = {
            'development': ('app.config.development_config', 'DevelopmentConfig'),
            'testing': ('app.config.testing_config', 'TestingConfig'),
            'production': ('app.config.production_config', 'ProductionConfig')
        }
        
        if app_config in config_mapping:
            module_path, class_name = config_mapping[app_config]
            config_module = importlib.import_module(module_path)
            config_class = getattr(config_module, class_name)
            app.config.from_object(config_class)
            print(f"Loaded configuration class: {class_name}")
        else:
            print(f"Unknown configuration: {app_config}")
            # Fall back to development config
            config_module = importlib.import_module('app.config.development_config')
            config_class = getattr(config_module, 'DevelopmentConfig')
            app.config.from_object(config_class)
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Set default database URI based on environment if not already set
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        if app_config == "development":
            app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://user:password@db:3306/subscription_dev_db"
        elif app_config == "testing":
            app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://user:password@test-db:3306/subscription_test_db"
        else:  # production
            app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI", 
                                   "mysql+pymysql://user:password@db:3306/subscription_db")
    
    # Make sure DEBUG and TESTING values are set properly
    print(f"DEBUG setting: {app.config.get('DEBUG')}")
    print(f"TESTING setting: {app.config.get('TESTING')}")
    
    # Print final database URI after config is loaded
    print(f"Final Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    
    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    
    # Initialize Flask-Migrate with app and database
    migrate.init_app(app, db)
    
    # Import models to ensure they're registered with SQLAlchemy
    from app.models import User, SubscriptionPlan, UserSubscription
    
    # Create API
    api = Api(
        app,
        version="1.0",
        title="Subscription Management API",
        description="A RESTful API for managing user subscriptions",
        doc="/api/docs",
    )
    
    # Register blueprints and namespaces here
    from app.api.auth import auth_ns
    # from app.api.subscriptions import subscription_ns
    api.add_namespace(auth_ns, path='/api/auth')
    # api.add_namespace(subscription_ns)
    
    # Create a health check route
    @app.route('/health')
    def health_check():
        """Health check endpoint to verify the application is running."""
        return jsonify({
            'status': 'healthy',
            'environment': app_config,
            'database_connected': _check_db_connection(app)
        })
    
    def _check_db_connection(app):
        """Check if the database connection is working."""
        try:
            with app.app_context():
                # Execute a simple query
                db.session.execute('SELECT 1')
                return True
        except Exception as e:
            print(f"Database connection error: {str(e)}")
            return False
    
    # Shell context processor
    @app.shell_context_processor
    def shell_context():
        return {"app": app, "db": db}
    
    return app 