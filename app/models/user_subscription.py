"""
User Subscription model for managing user subscriptions to plans.
"""
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import Index, and_, func, or_
from sqlalchemy.ext.hybrid import hybrid_property

from app import db

from .base import BaseModel


class SubscriptionStatus(Enum):
    """Enum for subscription status values."""
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PENDING = "pending"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    PAUSED = "paused"


class PaymentStatus(Enum):
    """Enum for payment status values."""
    PAID = "paid"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"


class UserSubscription(BaseModel):
    """
    User Subscription model for managing user subscriptions to plans.
    
    Attributes:
        user_id (int): Foreign key to User model
        plan_id (int): Foreign key to SubscriptionPlan model
        status (str): Current status of the subscription
        start_date (datetime): When the subscription starts
        end_date (datetime): When the subscription ends
        trial_end_date (datetime): When the trial period ends
        canceled_at (datetime): When the subscription was canceled
        current_period_start (datetime): Start of current billing period
        current_period_end (datetime): End of current billing period
        payment_status (str): Status of the latest payment
        quantity (int): Number of subscriptions (for seat-based plans)
        cancel_at_period_end (bool): Whether to cancel at period end
        auto_renew (bool): Whether to automatically renew
        subscription_metadata (str): JSON string for additional metadata
    """
    __tablename__ = 'user_subscriptions'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=SubscriptionStatus.PENDING.value)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    trial_end_date = db.Column(db.DateTime, nullable=True)
    canceled_at = db.Column(db.DateTime, nullable=True)
    current_period_start = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    current_period_end = db.Column(db.DateTime, nullable=True)
    payment_status = db.Column(db.String(20), nullable=False, default=PaymentStatus.PENDING.value)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    cancel_at_period_end = db.Column(db.Boolean, nullable=False, default=False)
    auto_renew = db.Column(db.Boolean, nullable=False, default=True)
    subscription_metadata = db.Column(db.Text, nullable=True)
    
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
        
        # Index for date-based queries
        Index('idx_user_subscription_start_date', 'start_date'),
        Index('idx_user_subscription_end_date', 'end_date'),
        Index('idx_user_subscription_current_period', 'current_period_start', 'current_period_end'),
        
        # Index for trial subscriptions
        Index('idx_user_subscription_trial_end', 'trial_end_date'),
        
        # Index for payment status
        Index('idx_user_subscription_payment', 'payment_status'),
        
        # Composite index for user's active subscriptions (common query)
        Index('idx_user_active_subscriptions', 'user_id', 'status'),
        
        # Composite index for subscription by user and plan (important for lookup)
        Index('idx_user_plan_subscription', 'user_id', 'plan_id'),
        
        # Composite index for renewal tracking
        Index('idx_user_subscription_renewal', 'auto_renew', 'current_period_end'),
        
        # Composite index for cancellation at period end
        Index('idx_user_subscription_cancel_period_end', 'cancel_at_period_end', 'current_period_end'),
        
        # Composite index for expiring trials (useful for notifications)
        Index('idx_user_subscription_trial_status', 'status', 'trial_end_date')
    )
    
    def __init__(self, user_id, plan_id, status=SubscriptionStatus.PENDING.value, 
                 start_date=None, end_date=None, trial_end_date=None,
                 current_period_start=None, current_period_end=None,
                 payment_status=PaymentStatus.PENDING.value,
                 quantity=1, cancel_at_period_end=False, auto_renew=True,
                 subscription_metadata=None):
        """
        Initialize a new UserSubscription instance.
        
        Args:
            user_id (int): User ID
            plan_id (int): Plan ID
            status (str, optional): Subscription status
            start_date (datetime, optional): Subscription start date
            end_date (datetime, optional): Subscription end date
            trial_end_date (datetime, optional): Trial end date
            current_period_start (datetime, optional): Current billing period start
            current_period_end (datetime, optional): Current billing period end
            payment_status (str, optional): Payment status
            quantity (int, optional): Number of subscriptions
            cancel_at_period_end (bool, optional): Whether to cancel at period end
            auto_renew (bool, optional): Whether to auto-renew
            subscription_metadata (str, optional): Additional metadata
        """
        self.user_id = user_id
        self.plan_id = plan_id
        self.status = status
        self.start_date = start_date or datetime.utcnow()
        self.end_date = end_date
        self.trial_end_date = trial_end_date
        self.current_period_start = current_period_start or datetime.utcnow()
        self.current_period_end = current_period_end
        self.payment_status = payment_status
        self.quantity = quantity
        self.cancel_at_period_end = cancel_at_period_end
        self.auto_renew = auto_renew
        self.subscription_metadata = subscription_metadata
    
    @hybrid_property
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
    
    @is_active.expression
    def is_active(cls):
        """
        SQLAlchemy expression for is_active property.
        
        Returns:
            SQLAlchemy expression: Query expression for active subscriptions
        """
        # Using func.now() instead of datetime.utcnow() for SQL expression
        # This ensures the datetime is evaluated at the database level
        return and_(
            cls.status == SubscriptionStatus.ACTIVE.value,
            cls.start_date <= func.now(),
            or_(
                cls.end_date == None,  # noqa: E711
                cls.end_date > func.now()
            )
        )
    
    @hybrid_property
    def is_trial(self):
        """
        Check if the subscription is in trial period.
        
        Returns:
            bool: True if in trial, False otherwise
        """
        now = datetime.utcnow()
        return (self.status == SubscriptionStatus.TRIAL.value and
                self.trial_end_date is not None and 
                self.trial_end_date > now)
    
    @is_trial.expression
    def is_trial(cls):
        """
        SQLAlchemy expression for is_trial property.
        
        Returns:
            SQLAlchemy expression: Query expression for trial subscriptions
        """
        # Using func.now() instead of datetime.utcnow() for SQL expression
        return and_(
            cls.status == SubscriptionStatus.TRIAL.value,
            cls.trial_end_date != None,  # noqa: E711
            cls.trial_end_date > func.now()
        )
    
    @hybrid_property
    def days_until_renewal(self):
        """
        Calculate the number of days until subscription renewal.
        
        Returns:
            int: Number of days until renewal or None if no renewal date
        """
        if not self.current_period_end or not self.auto_renew:
            return None
            
        now = datetime.utcnow()
        delta = self.current_period_end - now
        return max(0, delta.days)
    
    def activate(self):
        """Activate the subscription."""
        self.status = SubscriptionStatus.ACTIVE.value
        return self
    
    def cancel(self, at_period_end=True):
        """
        Cancel the subscription.
        
        Args:
            at_period_end (bool): Whether to cancel at period end or immediately
            
        Returns:
            UserSubscription: The subscription instance
        """
        now = datetime.utcnow()
        
        if at_period_end:
            self.cancel_at_period_end = True
            self.auto_renew = False
        else:
            self.status = SubscriptionStatus.CANCELED.value
            self.canceled_at = now
            self.end_date = now
            
        return self
    
    def start_trial(self, trial_days=14):
        """
        Start a trial period for the subscription.
        
        Args:
            trial_days (int): Number of days for trial
            
        Returns:
            UserSubscription: The subscription instance
        """
        now = datetime.utcnow()
        self.status = SubscriptionStatus.TRIAL.value
        self.trial_end_date = now + timedelta(days=trial_days)
        return self
    
    def renew(self, days=30):
        """
        Renew the subscription for another period.
        
        Args:
            days (int): Days to add to the subscription
            
        Returns:
            UserSubscription: The subscription instance
        """
        now = datetime.utcnow()
        self.current_period_start = now
        self.current_period_end = now + timedelta(days=days)
        
        if self.status != SubscriptionStatus.ACTIVE.value:
            self.status = SubscriptionStatus.ACTIVE.value
            
        if self.end_date and self.end_date < self.current_period_end:
            self.end_date = self.current_period_end
            
        return self
    
    def expire(self):
        """
        Mark the subscription as expired.
        
        Returns:
            UserSubscription: The subscription instance
        """
        self.status = SubscriptionStatus.EXPIRED.value
        self.end_date = datetime.utcnow()
        return self
    
    def pause(self):
        """
        Pause the subscription.
        
        Returns:
            UserSubscription: The subscription instance
        """
        self.status = SubscriptionStatus.PAUSED.value
        return self
        
    def resume(self):
        """
        Resume a paused or canceled subscription.
        
        Returns:
            UserSubscription: The subscription instance
        """
        self.status = SubscriptionStatus.ACTIVE.value
        self.cancel_at_period_end = False
        self.auto_renew = True
        return self
    
    def update_payment_status(self, status):
        """
        Update the payment status.
        
        Args:
            status (str): New payment status
            
        Returns:
            UserSubscription: The subscription instance
        """
        self.payment_status = status
        
        # If payment failed, update subscription status
        if status == PaymentStatus.FAILED.value:
            self.status = SubscriptionStatus.PAST_DUE.value
        
        return self
    
    def change_plan(self, new_plan_id, prorate=True):
        """
        Change subscription to a new plan.
        
        Args:
            new_plan_id (int): New plan ID
            prorate (bool): Whether to prorate the subscription
            
        Returns:
            UserSubscription: The subscription instance
        """
        self.plan_id = new_plan_id
        
        # In a real implementation, proration logic would be applied here
        # based on remaining time in current period
        
        return self
    
    @classmethod
    def get_active_subscription(cls, user_id):
        """
        Get a user's active subscription.
        
        Args:
            user_id (int): User ID
            
        Returns:
            UserSubscription: The active subscription or None
        """
        # First try direct query by status (most reliable)
        subscription = cls.query.filter_by(
            user_id=user_id, 
            status=SubscriptionStatus.ACTIVE.value
        ).first()
        
        # If found, verify it's actually active by our definition
        if subscription and subscription.is_active:
            return subscription
        
        # If not found or not actually active, try with the hybrid property
        return cls.query.filter(
            cls.user_id == user_id,
            cls.is_active
        ).first()
    
    @classmethod
    def get_expiring_subscriptions(cls, days=7):
        """
        Get subscriptions expiring soon.
        
        Args:
            days (int): Number of days to look ahead
            
        Returns:
            list: List of expiring subscriptions
        """
        expiry_date = datetime.utcnow() + timedelta(days=days)
        return cls.query.filter(
            cls.status == SubscriptionStatus.ACTIVE.value,
            cls.current_period_end <= expiry_date,
            cls.auto_renew == False  # noqa: E712
        ).all()
    
    @classmethod
    def get_user_subscription_history(cls, user_id):
        """
        Get a user's subscription history.
        
        Args:
            user_id (int): User ID
            
        Returns:
            list: List of user's subscriptions
        """
        return cls.query.filter(
            cls.user_id == user_id
        ).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_recent_subscriptions(cls, days=30, status=None):
        """
        Get recently created subscriptions.
        
        Args:
            days (int): Number of days to look back
            status (str, optional): Filter by status
            
        Returns:
            list: List of recent subscriptions
        """
        query = cls.query.filter(
            cls.created_at >= datetime.utcnow() - timedelta(days=days)
        )
        
        if status:
            query = query.filter(cls.status == status)
            
        return query.order_by(cls.created_at.desc()).all()
    
    def __repr__(self):
        """String representation of the UserSubscription model."""
        return f"<UserSubscription User:{self.user_id} Plan:{self.plan_id} Status:{self.status}>" 