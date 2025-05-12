"""
Subscription Plan model for managing available subscription plans.
"""
import json
from enum import Enum

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from app import db

from .base import BaseModel


class SubscriptionInterval(Enum):
    """Enum for subscription interval types."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly" 
    SEMI_ANNUAL = "semi-annual"
    ANNUAL = "annual"


class PlanStatus(Enum):
    """Enum for plan status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class SubscriptionPlan(BaseModel):
    """
    Subscription Plan model for managing different subscription offerings.
    
    Attributes:
        name (str): Plan name (e.g., "Basic", "Premium")
        description (str): Plan description
        price (float): Price of the plan
        interval (str): Billing interval (monthly, quarterly, annual, etc.)
        duration_months (int): Duration of the plan in months
        features (str): JSON string containing features included in the plan
        status (str): Plan status (active, inactive, deprecated)
        is_public (bool): Whether plan is publicly available for signup
        max_users (int): Maximum number of users allowed (for team/org plans)
        parent_id (int): Parent plan ID for hierarchical plan relationships
        sort_order (int): Display order for plans in UI
    """
    __tablename__ = 'subscription_plans'
    
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    interval = db.Column(db.String(20), nullable=False, default=SubscriptionInterval.MONTHLY.value)
    duration_months = db.Column(db.Integer, nullable=False, default=1)
    features = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=PlanStatus.ACTIVE.value)
    is_public = db.Column(db.Boolean, nullable=False, default=True)
    max_users = db.Column(db.Integer, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    
    subscriptions = db.relationship('UserSubscription', back_populates='plan', lazy='dynamic')
    child_plans = db.relationship(
        'SubscriptionPlan',
        backref=db.backref('parent', remote_side='SubscriptionPlan.id'),
        lazy='joined'
    )
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('name', 'interval', name='uix_plan_name_interval'),
        
        Index('idx_subscription_plan_status', 'status'),
        Index('idx_subscription_plan_price', 'price'),
        Index('idx_subscription_plan_parent', 'parent_id'),
        Index('idx_subscription_plan_public', 'is_public'),
        Index('idx_subscription_plan_sort', 'sort_order')
    )
    
    def __init__(self, name, description, price, 
                 interval=SubscriptionInterval.MONTHLY.value,
                 duration_months=1, 
                 features=None, 
                 status=PlanStatus.ACTIVE.value,
                 is_public=True,
                 max_users=None,
                 parent_id=None,
                 sort_order=0):
        """
        Initialize a new SubscriptionPlan instance.
        
        Args:
            name (str): Plan name
            description (str): Plan description
            price (float): Plan price
            interval (str, optional): Billing interval (monthly, quarterly, etc)
            duration_months (int, optional): Duration in months
            features (str or dict, optional): JSON string or dict of features
            status (str, optional): Plan status
            is_public (bool, optional): Whether plan is publicly available
            max_users (int, optional): Maximum users allowed (for team plans)
            parent_id (int, optional): Parent plan ID for hierarchical plans
            sort_order (int, optional): Display order for UI
        """
        self.name = name
        self.description = description
        self.price = price
        self.interval = interval
        self.duration_months = duration_months
        
        # Handle features as either JSON string or dict
        if isinstance(features, dict):
            self.features = json.dumps(features)
        else:
            self.features = features
            
        self.status = status
        self.is_public = is_public
        self.max_users = max_users
        self.parent_id = parent_id
        self.sort_order = sort_order
    
    @hybrid_property
    def is_active(self):
        """Check if plan is currently active."""
        return self.status == PlanStatus.ACTIVE.value
        
    @hybrid_property
    def monthly_price(self):
        """Calculate the monthly price equivalent for comparison."""
        if self.duration_months == 0:  # Handle potential divide-by-zero
            return self.price
        return self.price / self.duration_months
    
    def get_features_dict(self):
        """
        Get the features as a Python dictionary.
        
        Returns:
            dict: Dictionary of plan features
        """
        if not self.features:
            return {}
        try:
            return json.loads(self.features)
        except json.JSONDecodeError:
            return {}
    
    def set_features_dict(self, features_dict):
        """
        Set features from a Python dictionary.
        
        Args:
            features_dict (dict): Dictionary of plan features
        """
        self.features = json.dumps(features_dict)
    
    def has_feature(self, feature_key):
        """
        Check if plan has a specific feature.
        
        Args:
            feature_key (str): Feature key to check
            
        Returns:
            bool: True if feature exists and is enabled
        """
        features = self.get_features_dict()
        return features.get(feature_key, False)
    
    def __repr__(self):
        """String representation of the SubscriptionPlan model."""
        return f"<SubscriptionPlan {self.name} - {self.interval} - ${self.price}>" 