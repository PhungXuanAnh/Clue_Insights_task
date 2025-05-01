"""
Unit tests for UserSubscription model.
"""
import pytest
from datetime import datetime, timedelta
import time

from app.models import User, SubscriptionPlan, UserSubscription
from app.models.user_subscription import SubscriptionStatus, PaymentStatus


class TestUserSubscriptionModel:
    """Tests for the UserSubscription model."""

    def test_create_subscription(self, db):
        """Test creating a basic subscription."""
        # Create test user
        user = User(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        db.session.add(user)
        db.session.flush()

        # Create test plan
        plan = SubscriptionPlan(
            name="Basic Plan",
            description="Basic subscription plan for testing",
            price=9.99
        )
        db.session.add(plan)
        db.session.flush()

        # Create subscription
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value
        )
        db.session.add(subscription)
        db.session.commit()

        # Test subscription properties
        assert subscription.id is not None
        assert subscription.user_id == user.id
        assert subscription.plan_id == plan.id
        assert subscription.status == SubscriptionStatus.ACTIVE.value
        assert subscription.auto_renew is True
        assert subscription.cancel_at_period_end is False
        assert subscription.payment_status == PaymentStatus.PENDING.value
        assert subscription.quantity == 1

    def test_subscription_is_active(self, db):
        """Test is_active property."""
        # Create test user and plan
        user = User(username="activeuser", email="active@example.com", password="password123")
        plan = SubscriptionPlan(name="Active Plan", description="Test plan", price=19.99)
        db.session.add_all([user, plan])
        db.session.flush()

        # Create active subscription
        now = datetime.utcnow()
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

        # Test inactive status (expired)
        subscription.end_date = now - timedelta(days=1)
        db.session.commit()
        assert subscription.is_active is False

        # Test inactive status (not active)
        subscription.end_date = now + timedelta(days=25)
        subscription.status = SubscriptionStatus.CANCELED.value
        db.session.commit()
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
        now = datetime.utcnow()
        assert subscription.trial_end_date > now
        assert subscription.trial_end_date < now + timedelta(days=15)
        assert subscription.is_trial is True

        # Test expired trial
        subscription.trial_end_date = now - timedelta(days=1)
        db.session.commit()
        assert subscription.is_trial is False

    def test_cancel_subscription(self, db):
        """Test canceling a subscription."""
        # Create test user, plan and subscription
        user = User(username="canceluser", email="cancel@example.com", password="password123")
        plan = SubscriptionPlan(name="Cancel Plan", description="Plan to cancel", price=39.99)
        db.session.add_all([user, plan])
        db.session.flush()

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

        # Test immediate cancellation
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

        now = datetime.utcnow()
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
        
        assert subscription.current_period_start > old_period_end
        assert subscription.current_period_end > now
        assert (subscription.current_period_end - subscription.current_period_start).days <= 30

    def test_change_plan(self, db):
        """Test changing subscription plan."""
        # Create test user and plans
        user = User(username="changeuser", email="change@example.com", password="password123")
        plan1 = SubscriptionPlan(name="Basic Plan", description="Basic plan", price=9.99)
        plan2 = SubscriptionPlan(name="Premium Plan", description="Premium plan", price=19.99)
        db.session.add_all([user, plan1, plan2])
        db.session.flush()

        # Create subscription to basic plan
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan1.id,
            status=SubscriptionStatus.ACTIVE.value
        )
        db.session.add(subscription)
        db.session.commit()

        # Test changing to premium plan
        subscription.change_plan(plan2.id)
        db.session.commit()
        
        assert subscription.plan_id == plan2.id
        
    def test_get_user_subscription_history(self, db):
        """Test getting a user's subscription history."""
        # Create test user and plans
        user = User(username="historyuser", email="history@example.com", password="password123")
        plan1 = SubscriptionPlan(name="Basic History", description="Basic plan", price=9.99)
        plan2 = SubscriptionPlan(name="Premium History", description="Premium plan", price=19.99)
        db.session.add_all([user, plan1, plan2])
        db.session.flush()

        # Create first subscription and add delay to ensure created_at differs
        old_sub = UserSubscription(
            user_id=user.id,
            plan_id=plan1.id,
            status=SubscriptionStatus.EXPIRED.value,
            start_date=datetime.utcnow() - timedelta(days=60),
            end_date=datetime.utcnow() - timedelta(days=30)
        )
        db.session.add(old_sub)
        db.session.commit()
        
        # Sleep to ensure created_at timestamps are different
        time.sleep(1)
        
        # Create second subscription
        new_sub = UserSubscription(
            user_id=user.id,
            plan_id=plan2.id,
            status=SubscriptionStatus.ACTIVE.value,
            start_date=datetime.utcnow() - timedelta(days=29)
        )
        db.session.add(new_sub)
        db.session.commit()

        # Test getting history with default pagination (no filters)
        pagination = UserSubscription.get_user_subscription_history(user.id)
        assert pagination.total == 2
        assert len(pagination.items) == 2
        
        # Verify both subscriptions are in the history
        subscription_statuses = [sub.status for sub in pagination.items]
        assert SubscriptionStatus.ACTIVE.value in subscription_statuses
        assert SubscriptionStatus.EXPIRED.value in subscription_statuses
        
        # Verify the ordering by created_at desc (newest first)
        assert pagination.items[0].created_at > pagination.items[1].created_at
        
        # Test filter by active status
        active_pagination = UserSubscription.get_user_subscription_history(
            user.id, status=SubscriptionStatus.ACTIVE.value
        )
        assert active_pagination.total == 1
        assert active_pagination.items[0].status == SubscriptionStatus.ACTIVE.value
        
        # Test filter by date range
        now = datetime.utcnow()
        # This would get subscriptions created more than a day ago
        past_pagination = UserSubscription.get_user_subscription_history(
            user.id, 
            to_date=now - timedelta(days=1)
        )
        # Both were created just now, so nothing should be returned
        assert past_pagination.total == 0 