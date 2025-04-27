"""
User Subscription model for managing user subscriptions to plans.
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import Index

from app import db
from .base import BaseModel


class SubscriptionStatus(Enum):
    """Enum for subscription status values."""
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PENDING = "pending"


class UserSubscription(BaseModel):
    """
    User Subscription model for managing user subscriptions to plans.
    
    Attributes:
        user_id (int): Foreign key to User model
        plan_id (int): Foreign key to SubscriptionPlan model
        status (str): Current status of the subscription
        start_date (datetime): When the subscription starts
        end_date (datetime): When the subscription ends
    """
    __tablename__ = 'user_subscriptions'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=SubscriptionStatus.PENDING.value)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', back_populates='subscriptions')
    plan = db.relationship('SubscriptionPlan', back_populates='subscriptions')
    
    # Create indexes for common queries
    __table_args__ = (
        # Index for querying a user's subscriptions
        Index('idx_user_subscription_user_id', 'user_id'),
        
        # Index for querying subscriptions by plan
        Index('idx_user_subscription_plan_id', 'plan_id'),
        
        # Index for querying active subscriptions
        Index('idx_user_subscription_status', 'status'),
        
        # Index for querying subscriptions by date ranges
        Index('idx_user_subscription_start_date', 'start_date'),
        Index('idx_user_subscription_end_date', 'end_date'),
        
        # Composite index for user's active subscriptions (common query)
        Index('idx_user_active_subscriptions', 'user_id', 'status'),
        
        # Composite index for subscription by user and plan
        Index('idx_user_plan_subscription', 'user_id', 'plan_id')
    )
    
    def __init__(self, user_id, plan_id, status=SubscriptionStatus.PENDING.value, 
                 start_date=None, end_date=None):
        """
        Initialize a new UserSubscription instance.
        
        Args:
            user_id (int): User ID
            plan_id (int): Plan ID
            status (str, optional): Subscription status
            start_date (datetime, optional): Subscription start date
            end_date (datetime, optional): Subscription end date
        """
        self.user_id = user_id
        self.plan_id = plan_id
        self.status = status
        self.start_date = start_date or datetime.utcnow()
        self.end_date = end_date
    
    def is_active(self):
        """
        Check if the subscription is currently active.
        
        Returns:
            bool: True if active, False otherwise
        """
        now = datetime.utcnow()
        return (self.status == SubscriptionStatus.ACTIVE.value and
                self.start_date <= now and 
                (self.end_date is None or self.end_date > now))
    
    def __repr__(self):
        """String representation of the UserSubscription model."""
        return f"<UserSubscription User:{self.user_id} Plan:{self.plan_id} Status:{self.status}>" 