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
    """
    __tablename__ = 'users'
    
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Relationships
    subscriptions = db.relationship('UserSubscription', back_populates='user', lazy='dynamic')
    
    def __init__(self, username, email, password):
        """
        Initialize a new User instance.
        
        Args:
            username (str): User's username
            email (str): User's email
            password (str): User's password (will be hashed)
        """
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
    
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