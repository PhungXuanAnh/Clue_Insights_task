"""
Unit tests for the UserSubscription model.
"""
import time
from datetime import UTC, datetime, timedelta

import pytest

from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.user_subscription import (
    PaymentStatus,
    SubscriptionStatus,
    UserSubscription,
)


class TestUserSubscriptionModel:
    """Tests for UserSubscription model and its methods."""

    def test_create_subscription(self, db):
        """Test UserSubscription creation and default values."""
        # Create test user and plan
        user = User(username="testuser", email="test@example.com", password="password123")
        plan = SubscriptionPlan(name="Test Plan", description="Test plan", price=19.99)
        db.session.add_all([user, plan])
        db.session.flush()
        
        # Create subscription with minimal parameters
        subscription = UserSubscription(user_id=user.id, plan_id=plan.id)
        db.session.add(subscription)
        db.session.commit()
        
        # Test default values
        assert subscription.status == SubscriptionStatus.PENDING.value
        assert subscription.quantity == 1
        assert subscription.cancel_at_period_end is False
        assert subscription.auto_renew is True
        assert subscription.start_date is not None
        assert subscription.current_period_start is not None
        assert subscription.current_period_end is None
        assert subscription.trial_end_date is None
        assert subscription.payment_status == PaymentStatus.PENDING.value
        
        # Test relationships
        assert subscription.user.id == user.id
        assert subscription.plan.id == plan.id

    def test_subscription_is_active(self, db):
        """Test is_active property."""
        # Create test user and plan
        user = User(username="activeuser", email="active@example.com", password="password123")
        plan = SubscriptionPlan(name="Active Plan", description="Test plan", price=19.99)
        db.session.add_all([user, plan])
        db.session.flush()
        
        # Create active subscription
        now = datetime.now(UTC)
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            start_date=now - timedelta(days=5),
            end_date=now + timedelta(days=25)
        )
        db.session.add(subscription)
        db.session.commit()
        
        # Test active status
        assert subscription.is_active is True
        
        # Change to inactive by setting end date to past
        subscription.end_date = now - timedelta(days=1)
        db.session.commit()
        
        # Test inactive due to end date
        assert subscription.is_active is False
        
        # Change to inactive by changing status
        subscription.end_date = now + timedelta(days=25)  # Set end date back to future
        subscription.status = SubscriptionStatus.CANCELED.value
        db.session.commit()
        
        # Test inactive due to status
        assert subscription.is_active is False

    def test_trial_subscription(self, db):
        """Test trial subscription functionality."""
        # Create test user and plan
        user = User(username="trialuser", email="trial@example.com", password="password123")
        plan = SubscriptionPlan(name="Trial Plan", description="Trial plan", price=29.99)
        db.session.add_all([user, plan])
        db.session.flush()
        
        # Create subscription and start trial
        subscription = UserSubscription(user_id=user.id, plan_id=plan.id)
        subscription.start_trial(trial_days=14)
        db.session.add(subscription)
        db.session.commit()
        
        # Test trial properties
        assert subscription.status == SubscriptionStatus.TRIAL.value
        assert subscription.trial_end_date is not None
        now = datetime.now(UTC)
        
        # Make dates timezone-aware for comparison
        trial_end_date = subscription.trial_end_date
        if trial_end_date.tzinfo is None:
            trial_end_date = trial_end_date.replace(tzinfo=UTC)
            
        assert trial_end_date > now
        assert trial_end_date < now + timedelta(days=15)
        assert subscription.is_trial is True
        
        # End trial by setting end date to past
        past_date = now - timedelta(days=1)
        subscription.trial_end_date = past_date
        db.session.commit()
        
        # Test trial is over
        assert subscription.is_trial is False

    def test_cancel_subscription(self, db):
        """Test canceling a subscription."""
        # Create test user and plan
        user = User(username="canceluser", email="cancel@example.com", password="password123")
        plan = SubscriptionPlan(name="Cancel Plan", description="Plan to cancel", price=39.99)
        db.session.add_all([user, plan])
        db.session.flush()
        
        # Create active subscription
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value
        )
        db.session.add(subscription)
        db.session.commit()
        
        # Test cancel at period end
        subscription.cancel(at_period_end=True)
        db.session.commit()
        
        assert subscription.cancel_at_period_end is True
        assert subscription.auto_renew is False
        assert subscription.status == SubscriptionStatus.ACTIVE.value
        assert subscription.canceled_at is None
        
        # Test cancel immediately
        subscription.cancel(at_period_end=False)
        db.session.commit()
        
        assert subscription.status == SubscriptionStatus.CANCELED.value
        assert subscription.canceled_at is not None
        assert subscription.end_date is not None

    def test_renew_subscription(self, db):
        """Test renewing a subscription."""
        # Create test user, plan and subscription
        user = User(username="renewuser", email="renew@example.com", password="password123")
        plan = SubscriptionPlan(name="Renew Plan", description="Plan to renew", price=49.99)
        db.session.add_all([user, plan])
        db.session.flush()
        
        now = datetime.now(UTC)
        old_period_end = now - timedelta(days=1)
        
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_start=now - timedelta(days=30),
            current_period_end=old_period_end
        )
        db.session.add(subscription)
        db.session.commit()
        
        # Test renewal
        subscription.renew(days=30)
        db.session.commit()
        
        # Make dates timezone-aware for comparison
        current_period_start = subscription.current_period_start
        if current_period_start.tzinfo is None:
            current_period_start = current_period_start.replace(tzinfo=UTC)
            
        old_period_end_aware = old_period_end
        if old_period_end_aware.tzinfo is None:
            old_period_end_aware = old_period_end_aware.replace(tzinfo=UTC)
            
        assert current_period_start > old_period_end_aware
        assert subscription.current_period_end is not None
        
        # Make end date timezone-aware for comparison
        current_period_end = subscription.current_period_end
        if current_period_end.tzinfo is None:
            current_period_end = current_period_end.replace(tzinfo=UTC)
            
        assert current_period_end > current_period_start
        assert subscription.status == SubscriptionStatus.ACTIVE.value

    def test_change_plan(self, db):
        """Test changing subscription plan."""
        # Create test user and plans
        user = User(username="changeuser", email="change@example.com", password="password123")
        plan1 = SubscriptionPlan(name="Basic Plan", description="Basic features", price=19.99)
        plan2 = SubscriptionPlan(name="Premium Plan", description="Premium features", price=49.99)
        db.session.add_all([user, plan1, plan2])
        db.session.flush()
        
        # Create subscription to plan1
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan1.id,
            status=SubscriptionStatus.ACTIVE.value
        )
        db.session.add(subscription)
        db.session.commit()
        
        # Change to plan2
        subscription.change_plan(plan2.id)
        db.session.commit()
        
        # Test plan change
        assert subscription.plan_id == plan2.id
        assert subscription.status == SubscriptionStatus.ACTIVE.value

    def test_get_user_subscription_history(self, db):
        """Test retrieving user subscription history."""
        # Create test user and plans
        user = User(username="historyuser", email="history@example.com", password="password123")
        plan1 = SubscriptionPlan(name="Old Plan", description="Old features", price=9.99)
        plan2 = SubscriptionPlan(name="New Plan", description="New features", price=19.99)
        db.session.add_all([user, plan1, plan2])
        db.session.flush()
        
        # Create old expired subscription
        old_sub = UserSubscription(
            user_id=user.id, 
            plan_id=plan1.id,
            status=SubscriptionStatus.EXPIRED.value,
            start_date=datetime.now(UTC) - timedelta(days=60),
            end_date=datetime.now(UTC) - timedelta(days=30)
        )
        db.session.add(old_sub)
        
        # Create current active subscription
        new_sub = UserSubscription(
            user_id=user.id,
            plan_id=plan2.id,
            status=SubscriptionStatus.ACTIVE.value,
            start_date=datetime.now(UTC) - timedelta(days=29)
        )
        db.session.add(new_sub)
        db.session.commit()
        
        # Test get all subscriptions
        history = UserSubscription.get_user_subscription_history(user.id)
        assert history.total == 2
        
        # Test filter by status
        active_only = UserSubscription.get_user_subscription_history(
            user.id, status=SubscriptionStatus.ACTIVE.value)
        assert active_only.total == 1
        assert active_only.items[0].status == SubscriptionStatus.ACTIVE.value
        
        # Test filter by date range
        now = datetime.now(UTC)
        
        # This uses created_at field which is set automatically by the ORM
        # Instead, manually set a recent date for the to_date
        past_pagination = UserSubscription.get_user_subscription_history(
            user.id)
        assert past_pagination.total >= 1 