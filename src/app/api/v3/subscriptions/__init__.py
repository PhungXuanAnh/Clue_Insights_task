"""
V3 Subscription namespaces for managing subscription plans and user subscriptions.

These endpoints use optimized JOIN operations for improved performance.
"""
from flask_restx import Namespace

subscription_ns = Namespace(
    'subscriptions', 
    description='Optimized subscription operations with efficient JOIN queries'
)

plan_ns = Namespace(
    'plans',
    description='Optimized subscription plan operations with efficient JOIN queries'
)

from . import routes 