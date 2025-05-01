"""
Integration tests for user subscription API endpoints.
"""
import json
from datetime import UTC, datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.user_subscription import (
    PaymentStatus,
    SubscriptionStatus,
    UserSubscription,
)


@pytest.fixture
def user_token(app):
    """Create a test user and generate an access token."""
    with app.app_context():
        from app import db

        # Create test user
        user = User(username="testuser", email="test@example.com", password="password123")
        db.session.add(user)
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(identity=str(user.id))
        
        return {
            "token": access_token,
            "user_id": user.id
        }


def test_create_subscription(client, db, user_token):
    """Test creating a new subscription."""
    # Create a plan to subscribe to
    plan = SubscriptionPlan(
        name="Test Plan",
        description="Test subscription plan",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    subscription_data = {
        "plan_id": plan.id,
        "auto_renew": True
    }
    
    response = client.post(
        '/api/subscriptions/',
        data=json.dumps(subscription_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 201
    assert data['plan_id'] == plan.id
    assert data['user_id'] == user_token['user_id']
    assert data['status'] == SubscriptionStatus.ACTIVE.value
    
    # Check that subscription exists in database
    subscription = UserSubscription.query.filter_by(
        user_id=user_token['user_id'],
        plan_id=plan.id
    ).first()
    assert subscription is not None


def test_upgrade_subscription(client, db, user_token):
    """Test upgrading/downgrading a subscription."""
    # Create two plans: one basic and one premium
    basic_plan = SubscriptionPlan(
        name="Basic Plan",
        description="Basic features",
        price=9.99
    )
    premium_plan = SubscriptionPlan(
        name="Premium Plan",
        description="Premium features",
        price=29.99
    )
    db.session.add_all([basic_plan, premium_plan])
    db.session.commit()
    
    # Create an active subscription to the basic plan
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=basic_plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(minutes=5),
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        payment_status=PaymentStatus.PAID.value,
        end_date=None
    )
    db.session.add(subscription)
    db.session.commit()
    db.session.expire_all()
    
    # Upgrade to premium plan
    upgrade_data = {
        "plan_id": premium_plan.id,
        "prorate": True
    }
    
    response = client.post(
        '/api/subscriptions/upgrade',
        data=json.dumps(upgrade_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data}")
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['plan_id'] == premium_plan.id
    assert data['user_id'] == user_token['user_id']
    assert data['status'] == SubscriptionStatus.ACTIVE.value
    
    # Check that subscription was updated in database
    updated_subscription = UserSubscription.query.get(subscription.id)
    assert updated_subscription.plan_id == premium_plan.id


def test_upgrade_to_same_plan(client, db, user_token):
    """Test upgrading to the same plan (should fail)."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Standard Plan",
        description="Standard features",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Create an active subscription to the plan
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(minutes=5),
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        payment_status=PaymentStatus.PAID.value,
        end_date=None
    )
    db.session.add(subscription)
    db.session.commit()
    db.session.expire_all()
    
    # Try to upgrade to the same plan
    upgrade_data = {
        "plan_id": plan.id,
        "prorate": True
    }
    
    response = client.post(
        '/api/subscriptions/upgrade',
        data=json.dumps(upgrade_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    
    assert response.status_code == 400


def test_downgrade_subscription(client, db, user_token):
    """Test downgrading from a premium to a basic plan."""
    # Create two plans: one basic and one premium
    basic_plan = SubscriptionPlan(
        name="Basic Plan",
        description="Basic features",
        price=9.99
    )
    premium_plan = SubscriptionPlan(
        name="Premium Plan",
        description="Premium features",
        price=29.99
    )
    db.session.add_all([basic_plan, premium_plan])
    db.session.commit()
    
    # Create an active subscription to the premium plan
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=premium_plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(minutes=5),
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        payment_status=PaymentStatus.PAID.value,
        end_date=None
    )
    db.session.add(subscription)
    db.session.commit()
    db.session.expire_all()
    
    # Downgrade to basic plan
    downgrade_data = {
        "plan_id": basic_plan.id,
        "prorate": True
    }
    
    response = client.post(
        '/api/subscriptions/upgrade',
        data=json.dumps(downgrade_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['plan_id'] == basic_plan.id
    assert data['user_id'] == user_token['user_id']
    
    # Check that subscription was updated in database
    updated_subscription = UserSubscription.query.get(subscription.id)
    assert updated_subscription.plan_id == basic_plan.id


def test_upgrade_without_active_subscription(client, db, user_token):
    """Test upgrading without an active subscription (should fail)."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Standard Plan",
        description="Standard features",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Try to upgrade without an active subscription
    upgrade_data = {
        "plan_id": plan.id,
        "prorate": True
    }
    
    response = client.post(
        '/api/subscriptions/upgrade',
        data=json.dumps(upgrade_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    
    assert response.status_code == 404


def test_upgrade_to_inactive_plan(client, db, user_token):
    """Test upgrading to an inactive plan (should fail)."""
    # Create an active plan for the initial subscription
    active_plan = SubscriptionPlan(
        name="Active Plan",
        description="Currently active",
        price=9.99
    )
    
    # Create an inactive plan
    inactive_plan = SubscriptionPlan(
        name="Inactive Plan",
        description="Inactive plan",
        price=19.99,
        status="inactive"
    )
    db.session.add_all([active_plan, inactive_plan])
    db.session.commit()
    
    # Create an active subscription
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=active_plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        payment_status=PaymentStatus.PAID.value
    )
    db.session.add(subscription)
    db.session.commit()
    
    # Try to upgrade to the inactive plan
    upgrade_data = {
        "plan_id": inactive_plan.id,
        "prorate": True
    }
    
    response = client.post(
        '/api/subscriptions/upgrade',
        data=json.dumps(upgrade_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    
    assert response.status_code == 400 


def test_cancel_subscription(client, db, user_token):
    """Test canceling a subscription."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Standard Plan",
        description="Standard features",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Create an active subscription to the plan
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(minutes=5),
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        payment_status=PaymentStatus.PAID.value,
        end_date=None
    )
    db.session.add(subscription)
    db.session.commit()
    
    # Ensure the subscription is findable via is_active property
    db.session.expire_all()  # Clear the session to force a fresh load
    
    # Cancel the subscription
    cancel_data = {
        "at_period_end": True
    }
    
    response = client.post(
        '/api/subscriptions/cancel',
        data=json.dumps(cancel_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['user_id'] == user_token['user_id']
    assert data['cancel_at_period_end'] == True
    assert data['auto_renew'] == False
    assert data['status'] == SubscriptionStatus.ACTIVE.value
    
    # Check that subscription was updated in database
    updated_subscription = UserSubscription.query.get(subscription.id)
    assert updated_subscription.cancel_at_period_end == True
    assert updated_subscription.auto_renew == False


def test_cancel_subscription_immediately(client, db, user_token):
    """Test canceling a subscription immediately."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Standard Plan",
        description="Standard features",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Create an active subscription to the plan
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(minutes=5),  # Set start date to 5 minutes ago
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        payment_status=PaymentStatus.PAID.value,
        end_date=None
    )
    db.session.add(subscription)
    db.session.commit()
    
    # Ensure the subscription is findable via is_active property
    db.session.expire_all()  # Clear the session to force a fresh load
    
    # Cancel the subscription immediately
    cancel_data = {
        "at_period_end": False
    }
    
    response = client.post(
        '/api/subscriptions/cancel',
        data=json.dumps(cancel_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['user_id'] == user_token['user_id']
    assert data['status'] == SubscriptionStatus.CANCELED.value
    assert data['canceled_at'] is not None
    
    # Check that subscription was updated in database
    updated_subscription = UserSubscription.query.get(subscription.id)
    assert updated_subscription.status == SubscriptionStatus.CANCELED.value
    assert updated_subscription.canceled_at is not None


def test_cancel_without_active_subscription(client, db, user_token):
    """Test canceling without an active subscription (should fail)."""
    # Ensure there are no active subscriptions
    db.session.expire_all()  # Clear the session to force a fresh load
    
    # Cancel a non-existent subscription
    cancel_data = {
        "at_period_end": True
    }
    
    response = client.post(
        '/api/subscriptions/cancel',
        data=json.dumps(cancel_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    
    assert response.status_code == 404 


def test_get_subscription_history(client, db, user_token):
    """Test retrieving subscription history."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Test Plan",
        description="Test subscription plan",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Create a few subscriptions with different statuses
    now = datetime.now(UTC)
    subscriptions = [
        UserSubscription(
            user_id=user_token['user_id'],
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            start_date=now - timedelta(days=60),
            end_date=now - timedelta(days=30),
            current_period_start=now - timedelta(days=60),
            current_period_end=now - timedelta(days=30),
            payment_status=PaymentStatus.PAID.value
        ),
        UserSubscription(
            user_id=user_token['user_id'],
            plan_id=plan.id,
            status=SubscriptionStatus.CANCELED.value,
            start_date=now - timedelta(days=30),
            end_date=now - timedelta(days=1),
            canceled_at=now - timedelta(days=15),
            current_period_start=now - timedelta(days=30),
            current_period_end=now - timedelta(days=1),
            payment_status=PaymentStatus.PAID.value
        )
    ]
    db.session.add_all(subscriptions)
    db.session.commit()
    
    response = client.get(
        '/api/subscriptions/history',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert 'subscriptions' in data
    assert len(data['subscriptions']) == 2
    assert data['total'] == 2


def test_get_active_subscription(client, db, user_token):
    """Test getting active subscription."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Active Plan",
        description="Currently active subscription plan",
        price=29.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Create an active subscription
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(days=5),
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        payment_status=PaymentStatus.PAID.value,
        end_date=None
    )
    db.session.add(subscription)
    db.session.commit()
    
    response = client.get(
        '/api/subscriptions/active',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['plan_id'] == plan.id
    assert data['user_id'] == user_token['user_id']
    assert data['status'] == SubscriptionStatus.ACTIVE.value
    assert 'plan' in data
    assert data['plan']['name'] == plan.name
    assert float(data['plan']['price']) == float(plan.price)


def test_get_active_subscription_not_found(client, db, user_token):
    """Test getting active subscription when none exists."""
    response = client.get(
        '/api/subscriptions/active',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    
    assert response.status_code == 404 