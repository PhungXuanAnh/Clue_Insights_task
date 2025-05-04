"""
Unit tests for the SQL optimizations.
"""
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app import db
from app.models.subscription_plan import (
    PlanStatus,
    SubscriptionInterval,
    SubscriptionPlan,
)
from app.models.user import User
from app.models.user_subscription import SubscriptionStatus, UserSubscription
from app.utils.sql_optimizations import (
    get_expiring_subscriptions,
    get_public_plans,
    get_subscription_history,
    get_subscription_stats,
    get_user_active_subscription,
)


class TestSqlOptimizations:
    """Test the SQL optimization functions."""

    def test_get_user_active_subscription(self, app):
        """Test get_user_active_subscription() function."""
        with app.app_context():
            # Create a test user
            user = User(
                username="testuser", email="test@example.com", password="password"
            )
            db.session.add(user)
            db.session.commit()

            # Create a test plan
            plan = SubscriptionPlan(
                name="Test Plan",
                description="Test plan description",
                price=10.0,
                interval=SubscriptionInterval.MONTHLY.value,
                duration_months=1,
                features=json.dumps({"feature1": True, "feature2": False}),
                status=PlanStatus.ACTIVE.value,
                is_public=True,
            )
            db.session.add(plan)
            db.session.commit()

            # Create an active subscription
            subscription = UserSubscription(
                user_id=user.id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE.value,
                start_date=datetime.now(UTC) - timedelta(days=1),
                end_date=datetime.now(UTC) + timedelta(days=30),
                current_period_start=datetime.now(UTC) - timedelta(days=1),
                current_period_end=datetime.now(UTC) + timedelta(days=30),
                payment_status="paid",
                auto_renew=True,
            )
            db.session.add(subscription)
            db.session.commit()

            # Test the function
            result = get_user_active_subscription(user.id)

            # Check the result
            assert result is not None
            assert result["user_id"] == user.id
            assert result["plan_id"] == plan.id
            assert result["status"] == SubscriptionStatus.ACTIVE.value
            assert "plan" in result
            assert result["plan"]["name"] == plan.name
            assert result["plan"]["price"] == float(plan.price)

            # Test with a non-existent user
            assert get_user_active_subscription(999) is None

    def test_get_subscription_history(self, app):
        """Test get_subscription_history() function."""
        with app.app_context():
            # Create a test user
            user = User(
                username="testuser2", email="test2@example.com", password="password"
            )
            db.session.add(user)
            db.session.commit()

            # Create a test plan
            plan = SubscriptionPlan(
                name="Test Plan 2",
                description="Test plan description 2",
                price=20.0,
                interval=SubscriptionInterval.MONTHLY.value,
                duration_months=1,
                features=json.dumps({"feature1": True, "feature2": False}),
                status=PlanStatus.ACTIVE.value,
                is_public=True,
            )
            db.session.add(plan)
            db.session.commit()

            # Create multiple subscriptions with different statuses
            subscriptions = [
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.ACTIVE.value,
                    start_date=datetime.now(UTC) - timedelta(days=60),
                    end_date=datetime.now(UTC) + timedelta(days=30),
                ),
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.CANCELED.value,
                    start_date=datetime.now(UTC) - timedelta(days=90),
                    end_date=datetime.now(UTC) - timedelta(days=60),
                ),
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.EXPIRED.value,
                    start_date=datetime.now(UTC) - timedelta(days=120),
                    end_date=datetime.now(UTC) - timedelta(days=90),
                ),
            ]
            db.session.add_all(subscriptions)
            db.session.commit()

            # Test the function with no filters
            items, total, page, per_page, pages = get_subscription_history(user.id)
            assert total == 3
            assert len(items) == 3
            assert page == 1
            assert per_page == 10
            assert pages == 1

            # Test with status filter
            items, total, page, per_page, pages = get_subscription_history(
                user.id, status=SubscriptionStatus.ACTIVE.value
            )
            assert total == 1
            assert len(items) == 1
            assert items[0]["status"] == SubscriptionStatus.ACTIVE.value

            # Test with multiple statuses
            items, total, page, per_page, pages = get_subscription_history(
                user.id,
                status=[
                    SubscriptionStatus.CANCELED.value,
                    SubscriptionStatus.EXPIRED.value,
                ],
            )
            assert total == 2
            assert len(items) == 2

            # Test pagination
            items, total, page, per_page, pages = get_subscription_history(
                user.id, per_page=1, page=2
            )
            assert total == 3
            assert len(items) == 1
            assert page == 2
            assert per_page == 1
            assert pages == 3

    def test_get_public_plans(self, app):
        """Test get_public_plans() function."""
        with app.app_context():
            # Create test plans
            plans = [
                SubscriptionPlan(
                    name="Public Plan 1",
                    description="Public plan description 1",
                    price=10.0,
                    status=PlanStatus.ACTIVE.value,
                    is_public=True,
                    sort_order=1,
                ),
                SubscriptionPlan(
                    name="Public Plan 2",
                    description="Public plan description 2",
                    price=20.0,
                    status=PlanStatus.ACTIVE.value,
                    is_public=True,
                    sort_order=2,
                ),
                SubscriptionPlan(
                    name="Private Plan",
                    description="Private plan description",
                    price=30.0,
                    status=PlanStatus.ACTIVE.value,
                    is_public=False,
                    sort_order=3,
                ),
                SubscriptionPlan(
                    name="Inactive Plan",
                    description="Inactive plan description",
                    price=40.0,
                    status=PlanStatus.INACTIVE.value,
                    is_public=True,
                    sort_order=4,
                ),
            ]
            db.session.add_all(plans)
            db.session.commit()

            # Test the function with no filters
            items, total, page, per_page, pages = get_public_plans()
            assert total == 3  # 2 active public + 1 inactive public
            assert len(items) == 3

            # Test with status filter
            items, total, page, per_page, pages = get_public_plans(
                status=PlanStatus.ACTIVE.value
            )
            assert total == 2
            assert len(items) == 2
            assert all(item["status"] == PlanStatus.ACTIVE.value for item in items)

            # Test sort order
            assert items[0]["sort_order"] < items[1]["sort_order"]

            # Test pagination
            items, total, page, per_page, pages = get_public_plans(per_page=1, page=2)
            assert total == 3
            assert len(items) == 1
            assert page == 2
            assert per_page == 1
            assert pages == 3

    def test_get_expiring_subscriptions(self, app):
        """Test get_expiring_subscriptions() function."""
        with app.app_context():
            # Create a test user
            user = User(
                username="testuser3", email="test3@example.com", password="password"
            )
            db.session.add(user)
            db.session.commit()

            # Create a test plan
            plan = SubscriptionPlan(
                name="Test Plan 3",
                description="Test plan description 3",
                price=30.0,
                interval=SubscriptionInterval.MONTHLY.value,
                duration_months=1,
                status=PlanStatus.ACTIVE.value,
                is_public=True,
            )
            db.session.add(plan)
            db.session.commit()

            # Create subscriptions with different expiration dates
            subscriptions = [
                # Expires in 5 days, auto_renew=False (should be included)
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.ACTIVE.value,
                    start_date=datetime.now(UTC) - timedelta(days=25),
                    end_date=datetime.now(UTC) + timedelta(days=5),
                    current_period_start=datetime.now(UTC) - timedelta(days=25),
                    current_period_end=datetime.now(UTC) + timedelta(days=5),
                    auto_renew=False,
                ),
                # Expires in 5 days, but auto_renew=True (should not be included)
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.ACTIVE.value,
                    start_date=datetime.now(UTC) - timedelta(days=25),
                    end_date=datetime.now(UTC) + timedelta(days=5),
                    current_period_start=datetime.now(UTC) - timedelta(days=25),
                    current_period_end=datetime.now(UTC) + timedelta(days=5),
                    auto_renew=True,
                ),
                # Expires in 10 days, auto_renew=False (should be included with days=10)
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.ACTIVE.value,
                    start_date=datetime.now(UTC) - timedelta(days=20),
                    end_date=datetime.now(UTC) + timedelta(days=10),
                    current_period_start=datetime.now(UTC) - timedelta(days=20),
                    current_period_end=datetime.now(UTC) + timedelta(days=10),
                    auto_renew=False,
                ),
            ]
            db.session.add_all(subscriptions)
            db.session.commit()

            # Test the function with default days=7
            results = get_expiring_subscriptions()
            assert len(results) == 1

            # Test with days=10
            results = get_expiring_subscriptions(days=10)
            assert len(results) == 2

            # Test with days=3
            results = get_expiring_subscriptions(days=3)
            assert len(results) == 0

    def test_get_subscription_stats(self, app):
        """Test get_subscription_stats() function."""
        with app.app_context():
            # Clear existing data for this test
            db.session.execute(text("DELETE FROM user_subscriptions"))
            db.session.commit()
            
            # Create a test user
            user = User(username="testuser4", email="test4@example.com", password="password")
            db.session.add(user)
            db.session.commit()
            
            # Create a test plan
            plan = SubscriptionPlan(
                name="Test Plan 4",
                description="Test plan description 4",
                price=40.0,
                interval=SubscriptionInterval.MONTHLY.value,
                duration_months=1,
                status=PlanStatus.ACTIVE.value,
                is_public=True,
            )
            db.session.add(plan)
            db.session.commit()
            
            # Set up current time for the test
            now = datetime.now(UTC)
            
            # Create various subscriptions for statistics
            subscriptions = [
                # Active subscription 1
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.ACTIVE.value,
                    start_date=now - timedelta(days=15),
                    current_period_end=now + timedelta(days=15),
                    auto_renew=True,
                ),
                # Active subscription 2 (also expiring soon, but without auto-renew)
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.ACTIVE.value,
                    start_date=now - timedelta(days=25),
                    current_period_end=now + timedelta(days=5),
                    auto_renew=False,
                ),
                # Trial subscription
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.TRIAL.value,
                    start_date=now - timedelta(days=7),
                    trial_end_date=now + timedelta(days=7),
                ),
                # Recently canceled subscription
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.CANCELED.value,
                    start_date=now - timedelta(days=40),
                    canceled_at=now - timedelta(days=5),
                ),
                # Old subscription (outside 30-day window)
                UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.EXPIRED.value,
                    start_date=now - timedelta(days=60),
                    end_date=now - timedelta(days=40),
                ),
            ]
            
            # First add the subscriptions to the database
            db.session.add_all(subscriptions)
            db.session.commit()
            
            # Then update the created_at values
            # Make the first 4 subscriptions' created_at within the last 30 days
            for i, sub in enumerate(subscriptions):
                if i < 4:  # The first 4 subscriptions should be within the last 30 days
                    sub.created_at = now - timedelta(days=i * 5)  # Different creation dates within 30 days
                else:
                    sub.created_at = now - timedelta(days=60)  # Outside 30-day window
            
            # Commit the updated created_at values
            db.session.commit()
            
            # Test the function
            stats = get_subscription_stats()
            
            # Helper function to make date comparison timezone-safe
            def is_after(dt1, dt2):
                """Compare two datetimes safely, handling timezone differences."""
                if dt1 is None or dt2 is None:
                    return False
                    
                # Make sure both dates are timezone-aware
                if dt1.tzinfo is None:
                    dt1 = dt1.replace(tzinfo=UTC)
                if dt2.tzinfo is None:
                    dt2 = dt2.replace(tzinfo=UTC)
                    
                return dt1 > dt2
                
            def is_between(dt, start, end):
                """Check if a datetime is between start and end, handling timezones."""
                if dt is None:
                    return False
                    
                # Make sure all dates are timezone-aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=UTC)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=UTC)
                    
                return start < dt <= end
            
            # Verify statistics
            expected_active = sum(1 for s in subscriptions if s.status == SubscriptionStatus.ACTIVE.value)
            expected_trial = sum(1 for s in subscriptions if s.status == SubscriptionStatus.TRIAL.value 
                               and s.trial_end_date and is_after(s.trial_end_date, now))
            expected_expiring_soon = sum(1 for s in subscriptions 
                                      if s.status == SubscriptionStatus.ACTIVE.value 
                                      and not s.auto_renew 
                                      and s.current_period_end 
                                      and is_between(s.current_period_end, now, now + timedelta(days=7)))
            
            # For dates coming from the database, use the safe comparison helpers
            thirty_days_ago = now - timedelta(days=30)
            expected_new = sum(1 for s in subscriptions if is_after(s.created_at, thirty_days_ago) or 
                             (s.created_at.tzinfo is None and s.created_at > thirty_days_ago.replace(tzinfo=None)))
            
            expected_recently_canceled = sum(1 for s in subscriptions 
                                         if s.status == SubscriptionStatus.CANCELED.value 
                                         and s.canceled_at 
                                         and is_after(s.canceled_at, thirty_days_ago))
            
            assert stats["active_count"] == expected_active
            assert stats["trial_count"] == expected_trial
            assert stats["expiring_soon_count"] == expected_expiring_soon
            assert stats["new_count"] == expected_new
            assert stats["recently_canceled_count"] == expected_recently_canceled
            
            # Double-check specific expected counts based on our setup
            assert expected_active == 2
            assert expected_trial == 1
            assert expected_expiring_soon == 1
            assert expected_new == 4
            assert expected_recently_canceled == 1
