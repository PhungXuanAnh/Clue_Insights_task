"""
User model for authentication and user management.
"""
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from .base import BaseModel


class User(BaseModel):
    """
    User model for authentication and user management.
    
    Attributes:
        username (str): Unique username for user identification
        email (str): User's email address (unique)
        password_hash (str): Hashed password
        is_admin (bool): Flag indicating if the user has admin privileges
    """
    __tablename__ = 'users'
    
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    subscriptions = db.relationship('UserSubscription', back_populates='user', lazy='dynamic')
    
    def __init__(self, username, email, password, is_admin=False):
        """
        Initialize a new User instance.
        
        Args:
            username (str): User's username
            email (str): User's email
            password (str): User's password (will be hashed)
            is_admin (bool, optional): Whether the user has admin privileges
        """
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.is_admin = is_admin
    
    def check_password(self, password):
        """
        Verify a password against the stored hash.
        
        Args:
            password (str): Password to check
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        """String representation of the User model."""
        return f"<User {self.username}>" 