"""
User subscription model for handling user subscriptions to plans.
"""
import enum
from datetime import UTC, datetime, timedelta

from sqlalchemy import Index, and_, func, or_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import joinedload

from app import db
from app.models.base import BaseModel


class SubscriptionStatus(enum.Enum):
    """Enum for subscription status values."""
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    PENDING = "pending"
    TRIAL = "trial"
    CHANGED = "changed"
    
    @classmethod
    def values(cls):
        """Get all enum values."""
        return [e.value for e in cls]


class PaymentStatus(enum.Enum):
    """Enum for payment status values."""
    PAID = "paid"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"
    
    @classmethod
    def values(cls):
        """Get all enum values."""
        return [e.value for e in cls]


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
    start_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    end_date = db.Column(db.DateTime, nullable=True)
    trial_end_date = db.Column(db.DateTime, nullable=True)
    canceled_at = db.Column(db.DateTime, nullable=True)
    current_period_start = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    current_period_end = db.Column(db.DateTime, nullable=True)
    payment_status = db.Column(db.String(20), nullable=False, default=PaymentStatus.PENDING.value)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    cancel_at_period_end = db.Column(db.Boolean, nullable=False, default=False)
    auto_renew = db.Column(db.Boolean, nullable=False, default=True)
    subscription_metadata = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User', back_populates='subscriptions')
    plan = db.relationship('SubscriptionPlan', back_populates='subscriptions')
    
    # Create indexes for common queries
    __table_args__ = (
        # Composite index for active subscriptions by user
        Index('idx_user_subscription_user_status', 'user_id', 'status'),
        
        # Composite index for expiring subscriptions (useful for renewal reminders)
        Index('idx_user_subscription_status_period_end', 'status', 'current_period_end'),
        
        # Composite index for expiring trials (useful for notifications)
        Index('idx_user_subscription_trial_status', 'status', 'trial_end_date'),
        
        # Add composite index for user_id and status for efficient lookup of active subscriptions
        Index('idx_user_subscriptions_user_id_status', 'user_id', 'status'),
        
        # Add composite index for status and end_date for filtering by status and end_date
        Index('idx_user_subscriptions_status_end_date', 'status', 'end_date'),
        
        # Add composite index for status and current_period_end for filtering by status and current_period_end
        Index('idx_user_subscriptions_status_current_period_end', 'status', 'current_period_end'),
        
        # New index for optimizing JOIN operations between UserSubscription and SubscriptionPlan
        Index('idx_user_subscriptions_plan_join', 'user_id', 'plan_id', 'status'),
    )
    
    def __init__(self, user_id, plan_id, status=SubscriptionStatus.PENDING.value, 
                 start_date=None, end_date=None, trial_end_date=None,
                 current_period_start=None, current_period_end=None,
                 payment_status=PaymentStatus.PENDING.value,
                 quantity=1, cancel_at_period_end=False, auto_renew=True,
                 subscription_metadata=None, canceled_at=None):
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
            canceled_at (datetime, optional): When the subscription was canceled
        """
        self.user_id = user_id
        self.plan_id = plan_id
        self.status = status
        self.start_date = start_date or datetime.now(UTC)
        self.end_date = end_date
        self.trial_end_date = trial_end_date
        self.current_period_start = current_period_start or datetime.now(UTC)
        self.current_period_end = current_period_end
        self.payment_status = payment_status
        self.quantity = quantity
        self.cancel_at_period_end = cancel_at_period_end
        self.auto_renew = auto_renew
        self.subscription_metadata = subscription_metadata
        self.canceled_at = canceled_at
    
    @hybrid_property
    def is_active(self):
        """
        Check if the subscription is currently active.
        
        Returns:
            bool: True if active, False otherwise
        """
        now = datetime.now(UTC)
        start_date = self.start_date
        end_date = self.end_date
        
        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=UTC)
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=UTC)
        
        return (self.status == SubscriptionStatus.ACTIVE.value and
                start_date <= now and 
                (end_date is None or end_date > now))
    
    @is_active.expression
    def is_active(cls):
        """
        SQLAlchemy expression for is_active property.
        
        Returns:
            SQLAlchemy expression: Query expression for active subscriptions
        """
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
        now = datetime.now(UTC)
        trial_end_date = self.trial_end_date
        if trial_end_date and trial_end_date.tzinfo is None:
            trial_end_date = trial_end_date.replace(tzinfo=UTC)
        
        return (self.status == SubscriptionStatus.TRIAL.value and
                trial_end_date is not None and 
                trial_end_date > now)
    
    @is_trial.expression
    def is_trial(cls):
        """
        SQLAlchemy expression for is_trial property.
        
        Returns:
            SQLAlchemy expression: Query expression for trial subscriptions
        """
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
            
        now = datetime.now(UTC)
        current_period_end = self.current_period_end
        if current_period_end and current_period_end.tzinfo is None:
            current_period_end = current_period_end.replace(tzinfo=UTC)
            
        delta = current_period_end - now
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
        now = datetime.now(UTC)
        
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
        now = datetime.now(UTC)
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
        now = datetime.now(UTC)
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
        self.end_date = datetime.now(UTC)
        self.auto_renew = False
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
        
        Optimized query that:
            1. Uses the composite index idx_user_active_subscriptions
            2. Eagerly loads the plan relationship to avoid N+1 query problems
            3. Uses proper date filtering at the database level
        """
        
        now = datetime.now(UTC)
        
        subscription = cls.query.options(
            joinedload(cls.plan)  # Eager load plan details
        ).filter(
            cls.user_id == user_id,
            cls.status == SubscriptionStatus.ACTIVE.value,
            cls.start_date <= now,
            or_(
                cls.end_date.is_(None),
                cls.end_date > now
            )
        ).first()
        
        # If not found, try looking for trial subscriptions that are still valid
        if not subscription:
            subscription = cls.query.options(
                joinedload(cls.plan)  # Eager load plan details
            ).filter(
                cls.user_id == user_id,
                cls.status == SubscriptionStatus.TRIAL.value,
                cls.trial_end_date.isnot(None),
                cls.trial_end_date > now
            ).first()
        
        return subscription
    
    @classmethod
    def get_expiring_subscriptions(cls, days=7):
        """
        Get subscriptions expiring soon.
        
        Args:
            days (int): Number of days to look ahead
            
        Returns:
            list: List of expiring subscriptions
        """
        expiry_date = datetime.now(UTC) + timedelta(days=days)
        return cls.query.filter(
            cls.status == SubscriptionStatus.ACTIVE.value,
            cls.current_period_end <= expiry_date,
            cls.auto_renew == False  # noqa: E712
        ).all()
    
    @classmethod
    def get_user_subscription_history(cls, user_id, status=None, from_date=None, to_date=None, page=1, per_page=10):
        """
        Get a user's subscription history with advanced filtering and pagination.
        
        Args:
            user_id (int): User ID
            status (str or list, optional): Filter by status or list of statuses
            from_date (datetime, optional): Filter subscriptions created after this date
            to_date (datetime, optional): Filter subscriptions created before this date
            page (int): Page number (for pagination)
            per_page (int): Items per page (for pagination)
            
        Returns:
            Pagination: SQLAlchemy pagination object with subscriptions and metadata
            
        Optimization strategies:
            - Eagerly loads plan details to avoid N+1 query problems
            - Uses composite indexes for efficient querying
            - Provides pagination for handling large result sets
            - Offers flexible filtering by status and date ranges
            - Sorts by most recent first to show newest subscriptions
        """
        query = cls.query.options(
            joinedload(cls.plan)
        ).filter(
            cls.user_id == user_id
        )
        
        if status:
            if isinstance(status, list):
                query = query.filter(cls.status.in_(status))
            else:
                query = query.filter(cls.status == status)
        
        if from_date:
            query = query.filter(cls.created_at >= from_date)
        
        if to_date:
            query = query.filter(cls.created_at <= to_date)
        
        return query.order_by(cls.created_at.desc()).paginate(
            page=page, per_page=per_page
        )
    
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
            cls.created_at >= datetime.now(UTC) - timedelta(days=days)
        )
        
        if status:
            query = query.filter(cls.status == status)
            
        return query.order_by(cls.created_at.desc()).all()
    
    def __repr__(self):
        """String representation of the UserSubscription model."""
        return f"<UserSubscription User:{self.user_id} Plan:{self.plan_id} Status:{self.status}>" 