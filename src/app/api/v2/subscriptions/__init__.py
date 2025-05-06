"""
V2 Subscription namespaces for managing subscription plans and user subscriptions.

These endpoints use direct SQL queries for improved performance.
"""
from flask_restx import Namespace

subscription_ns = Namespace(
    'subscriptions', 
    description='Optimized subscription operations with raw SQL'
)

plan_ns = Namespace(
    'plans',
    description='Optimized subscription plans operations with raw SQL'
)

from . import routes 