"""
Token blacklist model for handling revoked JWT tokens.
"""
from datetime import datetime

from app import db
from app.models.base import BaseModel


class TokenBlacklist(BaseModel):
    """
    Token blacklist model for storing revoked tokens.
    """
    __tablename__ = 'token_blacklist'

    jti = db.Column(db.String(36), nullable=False, index=True, unique=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('blacklisted_tokens', lazy='dynamic'))
    
    def __repr__(self):
        """String representation of the model."""
        return f'<TokenBlacklist {self.jti}>'
    
    @classmethod
    def is_token_revoked(cls, jti):
        """
        Check if the given token is blacklisted.
        
        Args:
            jti: The token identifier.
            
        Returns:
            bool: True if the token is blacklisted, False otherwise.
        """
        return cls.query.filter_by(jti=jti).first() is not None
    
    @classmethod
    def add_token_to_blacklist(cls, jti, token_type, user_id, expires_at):
        """
        Add a token to the blacklist.
        
        Args:
            jti: The token identifier.
            token_type: The type of token (access or refresh).
            user_id: The user identifier.
            expires_at: The token expiration date.
            
        Returns:
            TokenBlacklist: The created token blacklist entry.
        """
        token = cls(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at
        )
        db.session.add(token)
        db.session.commit()
        return token 