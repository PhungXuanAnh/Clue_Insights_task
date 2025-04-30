"""
Subscriptions namespace for managing subscription plans and user subscriptions.
"""
from flask_restx import Namespace

subscription_ns = Namespace(
    'subscriptions', 
    description='Subscription plans and user subscriptions operations'
)

plan_ns = Namespace(
    'plans',
    description='Subscription plans operations'
)

from . import routes 