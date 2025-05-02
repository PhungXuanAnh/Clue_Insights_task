"""
Subscription Management API Application Factory.
"""
import importlib
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, render_template, request, render_template_string
from flask_jwt_extended import JWTManager, get_jwt
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
    
    # Configure JWT token blacklist if enabled
    if app.config.get('JWT_BLACKLIST_ENABLED'):
        # Import token blacklist model
        from app.models.token_blacklist import TokenBlacklist
        
        @jwt.token_in_blocklist_loader
        def check_if_token_revoked(jwt_header, jwt_payload):
            """
            Check if a token is revoked.
            """
            jti = jwt_payload["jti"]
            return TokenBlacklist.is_token_revoked(jti)
            
        @jwt.revoked_token_loader
        def revoked_token_callback(jwt_header, jwt_payload):
            """
            Return a response when a revoked token is used.
            """
            return jsonify({
                'status': 401,
                'message': 'Token has been revoked'
            }), 401
    
    # Initialize Flask-Migrate with app and database
    migrate.init_app(app, db)
    
    # Import models to ensure they're registered with SQLAlchemy
    from app.models import (SubscriptionPlan, TokenBlacklist, User,
                            UserSubscription)

    # Create API with additional configuration for Swagger UI documentation
    api = Api(
        app,
        version=app.config.get("API_VERSION", "1.0"),
        title=app.config.get("API_TITLE", "Subscription Management API"),
        description=app.config.get("API_DESCRIPTION", "A RESTful API for managing user subscriptions"),
        doc="/api/docs",
        authorizations={
            'Bearer Auth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'Enter: **Bearer &lt;JWT&gt;**'
            },
        },
        security='Bearer Auth'  # Use Bearer Auth by default for all endpoints
    )
    
    # Register blueprints and namespaces here
    from app.api.auth import auth_ns
    from app.api.subscriptions import plan_ns, subscription_ns

    api.add_namespace(auth_ns, path='/api/auth')
    api.add_namespace(plan_ns, path='/api/plans')
    api.add_namespace(subscription_ns, path='/api/subscriptions')
    
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
    
    # Initialize DevToolbar extension for JSON responses
    if app_config == 'development' and app.config.get('DEBUG'):
        # Define a simple HTML template for wrapping JSON
        json_wrapper_template = """
        <html>
            <head>
                <title>Debugging JSON Response</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #333; }
                    pre { background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow: auto; max-height: 500px; }
                </style>
            </head>
            <body>
                <h1>JSON Response with Debug Toolbar</h1>
                <h2>HTTP Status: {{ http_code }}</h2>
                <h2>JSON Response</h2>
                <pre>{{ response }}</pre>
            </body>
        </html>
        """
        
        # Create after_request handler before initializing the debug toolbar
        @app.after_request
        def after_request(response):
            """
            Wrap JSON responses in HTML when _debug=true is in the URL params
            """
            if (response.mimetype == "application/json" and 
                request.args.get('_debug') == 'true'):
                
                # Create HTML response wrapping the JSON
                html_wrapped_response = make_response(
                    render_template_string(
                        json_wrapper_template,
                        response=response.get_data(as_text=True),
                        http_code=response.status
                    ),
                    response.status_code
                )
                
                # Let Flask application process the response
                # This ensures the debug toolbar is added correctly
                return app.process_response(html_wrapped_response)
                
            return response

        # Now initialize the Flask-DebugToolbar
        try:
            from flask_debugtoolbar import DebugToolbarExtension
            
            # Configure Flask-DebugToolbar
            app.config['DEBUG_TB_ENABLED'] = True
            app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
            app.config['DEBUG_TB_PROFILER_ENABLED'] = True
            
            # Initialize the extension
            with app.app_context():
                DebugToolbarExtension(app)
                print("Flask-DebugToolbar initialized in development mode")
        except ImportError:
            print("Flask-DebugToolbar not available, skipping initialization")
    
    return app 