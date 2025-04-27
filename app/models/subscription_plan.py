"""
Subscription Plan model for managing available subscription plans.
"""
from app import db
from .base import BaseModel


class SubscriptionPlan(BaseModel):
    """
    Subscription Plan model for managing different subscription offerings.
    
    Attributes:
        name (str): Plan name (e.g., "Basic", "Premium")
        description (str): Plan description
        price (float): Price of the plan
        features (str): JSON string containing features included in the plan
    """
    __tablename__ = 'subscription_plans'
    
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    features = db.Column(db.Text, nullable=True)
    
    # Relationships
    subscriptions = db.relationship('UserSubscription', back_populates='plan', lazy='dynamic')
    
    def __init__(self, name, description, price, features=None):
        """
        Initialize a new SubscriptionPlan instance.
        
        Args:
            name (str): Plan name
            description (str): Plan description
            price (float): Plan price
            features (str, optional): JSON string of features
        """
        self.name = name
        self.description = description
        self.price = price
        self.features = features
    
    def __repr__(self):
        """String representation of the SubscriptionPlan model."""
        return f"<SubscriptionPlan {self.name} - ${self.price}>" 