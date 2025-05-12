"""
Authentication routes for API v1.
"""
from datetime import datetime

from flask import current_app, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_restx import Resource, fields
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User

from . import auth_ns

register_model = auth_ns.model('UserRegistration', {
    'username': fields.String(required=True, description='User username'),
    'email': fields.String(required=True, description='User email address'),
    'password': fields.String(required=True, description='User password')
})

login_model = auth_ns.model('UserLogin', {
    'username': fields.String(required=True, description='User username or email'),
    'password': fields.String(required=True, description='User password')
})

token_model = auth_ns.model('TokenResponse', {
    'access_token': fields.String(description='JWT access token'),
    'refresh_token': fields.String(description='JWT refresh token'),
    'user_id': fields.Integer(description='User identifier'),
    'username': fields.String(description='User username'),
    'is_admin': fields.Boolean(description='Whether the user has admin privileges')
})

user_model = auth_ns.model('User', {
    'id': fields.Integer(description='User identifier'),
    'username': fields.String(description='User username'),
    'email': fields.String(description='User email address'),
    'is_admin': fields.Boolean(description='Whether the user has admin privileges'),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'updated_at': fields.DateTime(description='Last update timestamp')
})

refresh_token_model = auth_ns.model('RefreshToken', {
    'access_token': fields.String(description='New JWT access token')
})

logout_model = auth_ns.model('LogoutResponse', {
    'message': fields.String(description='Logout success message')
})

@auth_ns.route('/register')
class UserRegistration(Resource):
    """
    User registration endpoint.
    """
    @auth_ns.doc('register_user')
    @auth_ns.expect(register_model)
    @auth_ns.response(201, 'User successfully created', user_model)
    @auth_ns.response(400, 'Validation error')
    @auth_ns.response(409, 'User already exists')
    def post(self):
        """
        Register a new user.
        """
        data = request.json
        
        # Validate required fields
        if not all(k in data for k in ('username', 'email', 'password')):
            return {'message': 'Missing required fields'}, 400
            
        # Validate email format (basic validation)
        if '@' not in data['email']:
            return {'message': 'Invalid email format'}, 400
            
        # Validate password strength (basic validation)
        if len(data['password']) < 6:
            return {'message': 'Password must be at least 6 characters long'}, 400
            
        try:
            user = User(
                username=data['username'],
                email=data['email'],
                password=data['password']
            )
            db.session.add(user)
            db.session.commit()
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat(),
                'updated_at': user.updated_at.isoformat()
            }, 201
            
        except IntegrityError:
            db.session.rollback()
            return {'message': 'Username or email already exists'}, 409
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error creating user: {str(e)}'}, 500

@auth_ns.route('/login')
class UserLogin(Resource):
    """
    User login endpoint.
    """
    @auth_ns.doc('login_user')
    @auth_ns.expect(login_model)
    @auth_ns.response(200, 'Login successful', token_model)
    @auth_ns.response(400, 'Validation error')
    @auth_ns.response(401, 'Invalid credentials')
    def post(self):
        """
        Authenticate a user and generate JWT tokens.
        """
        data = request.json
        if not all(k in data for k in ('username', 'password')):
            return {'message': 'Missing required fields'}, 400
            
        user = User.query.filter(
            (User.username == data['username']) | (User.email == data['username'])
        ).first()
        
        if not user or not user.check_password(data['password']):
            return {'message': 'Invalid username/email or password'}, 401
            
        # Generate access and refresh tokens
        # Use custom claims to include admin status
        additional_claims = {"is_admin": user.is_admin}
        
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims=additional_claims
        )
        
        refresh_token = create_refresh_token(
            identity=str(user.id),
            additional_claims=additional_claims
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user_id': user.id,
            'username': user.username,
            'is_admin': user.is_admin
        }, 200

@auth_ns.route('/refresh')
class TokenRefresh(Resource):
    """
    Token refresh endpoint.
    """
    @auth_ns.doc('refresh_token')
    @jwt_required(refresh=True)
    @auth_ns.response(200, 'Token refresh successful', refresh_token_model)
    @auth_ns.response(401, 'Invalid refresh token')
    def post(self):
        """
        Generate a new access token using a refresh token.
        """
        current_user = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user)
        return {
            'access_token': new_access_token
        }, 200

@auth_ns.route('/logout')
class UserLogout(Resource):
    """
    User logout endpoint.
    """
    @auth_ns.doc('logout_user')
    @jwt_required()
    @auth_ns.response(200, 'Logout successful', logout_model)
    @auth_ns.response(401, 'Invalid token')
    def post(self):
        """
        Revoke the current JWT token.
        """
        if not current_app.config.get('JWT_BLACKLIST_ENABLED', False):
            return {'message': 'Logout successful'}, 200
            
        token_data = get_jwt()
        jti = token_data['jti']
        token_type = "access"
        user_id = get_jwt_identity()
        
        expires_at = datetime.fromtimestamp(token_data['exp'])
        
        try:
            TokenBlacklist.add_token_to_blacklist(
                jti=jti,
                token_type=token_type,
                user_id=int(user_id),
                expires_at=expires_at
            )
            return {'message': 'Successfully logged out'}, 200
        except Exception as e:
            return {'message': f'Error during logout: {str(e)}'}, 500 