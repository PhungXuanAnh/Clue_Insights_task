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


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_create_subscription(client, db, user_token, api_version):
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
        f'{api_version}/subscriptions/',
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


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_upgrade_subscription(client, db, user_token, api_version):
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
        f'{api_version}/subscriptions/upgrade',
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
    updated_subscription = db.session.get(UserSubscription, subscription.id)
    assert updated_subscription.plan_id == premium_plan.id


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_upgrade_to_same_plan(client, db, user_token, api_version):
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
        f'{api_version}/subscriptions/upgrade',
        data=json.dumps(upgrade_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    
    assert response.status_code == 400


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_downgrade_subscription(client, db, user_token, api_version):
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
        start_date=now - timedelta(days=15),
        current_period_start=now - timedelta(days=15),
        current_period_end=now + timedelta(days=15),
        payment_status=PaymentStatus.PAID.value,
        end_date=None
    )
    db.session.add(subscription)
    db.session.commit()
    db.session.expire_all()
    
    # Downgrade to basic plan
    downgrade_data = {
        "plan_id": basic_plan.id,
        "prorate": False
    }
    
    response = client.post(
        f'{api_version}/subscriptions/upgrade',
        data=json.dumps(downgrade_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['plan_id'] == basic_plan.id
    
    # Check that subscription was updated in database
    updated_subscription = db.session.get(UserSubscription, subscription.id)
    assert updated_subscription.plan_id == basic_plan.id


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_upgrade_without_active_subscription(client, db, user_token, api_version):
    """Test trying to upgrade without an active subscription."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Premium Plan",
        description="Premium features",
        price=29.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Try to upgrade without an existing subscription
    upgrade_data = {
        "plan_id": plan.id
    }
    
    response = client.post(
        f'{api_version}/subscriptions/upgrade',
        data=json.dumps(upgrade_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    
    assert response.status_code == 404


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_upgrade_to_inactive_plan(client, db, user_token, api_version):
    """Test upgrading to an inactive plan."""
    # Create an active plan for the initial subscription
    active_plan = SubscriptionPlan(
        name="Active Plan",
        description="Active plan for subscription",
        price=19.99,
        status="active"
    )

    # Create an inactive plan for the upgrade attempt
    inactive_plan = SubscriptionPlan(
        name="Inactive Plan",
        description="Inactive plan",
        price=29.99,
        status="inactive"
    )

    db.session.add_all([active_plan, inactive_plan])
    db.session.commit()

    # Create an active subscription to the active plan
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=active_plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(days=5),
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        payment_status=PaymentStatus.PAID.value
    )
    db.session.add(subscription)
    db.session.commit()

    # Attempt to upgrade to the inactive plan
    upgrade_data = {
        "plan_id": inactive_plan.id,
        "prorate": True
    }

    response = client.post(
        f'{api_version}/subscriptions/upgrade',
        data=json.dumps(upgrade_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )

    # v1 responds with 400, v3 responds with 404 - checking both
    assert response.status_code in [400, 404]


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_cancel_subscription(client, db, user_token, api_version):
    """Test canceling a subscription at period end."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Test Plan",
        description="Test plan for cancellation",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Create an active subscription
    now = datetime.now(UTC)
    period_end = now + timedelta(days=30)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(days=5),
        current_period_start=now,
        current_period_end=period_end,
        payment_status=PaymentStatus.PAID.value
    )
    db.session.add(subscription)
    db.session.commit()
    db.session.expire_all()
    
    # Cancel the subscription at period end
    cancel_data = {
        "at_period_end": True
    }
    
    response = client.post(
        f'{api_version}/subscriptions/cancel',
        data=json.dumps(cancel_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == SubscriptionStatus.ACTIVE.value
    assert data['cancel_at_period_end'] is True
    
    # Check database updates
    updated_subscription = db.session.get(UserSubscription, subscription.id)
    assert updated_subscription.status == SubscriptionStatus.ACTIVE.value
    assert updated_subscription.canceled_at is not None
    assert updated_subscription.cancel_at_period_end is True


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_cancel_subscription_immediately(client, db, user_token, api_version):
    """Test canceling a subscription immediately."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Test Plan",
        description="Test plan for immediate cancellation",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Create an active subscription
    now = datetime.now(UTC)
    period_end = now + timedelta(days=30)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(days=5),
        current_period_start=now,
        current_period_end=period_end,
        payment_status=PaymentStatus.PAID.value
    )
    db.session.add(subscription)
    db.session.commit()
    db.session.expire_all()
    
    # Cancel the subscription immediately
    cancel_data = {
        "at_period_end": False
    }
    
    response = client.post(
        f'{api_version}/subscriptions/cancel',
        data=json.dumps(cancel_data),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == SubscriptionStatus.CANCELED.value
    assert data['end_date'] is not None
    
    # Check database updates
    updated_subscription = db.session.get(UserSubscription, subscription.id)
    assert updated_subscription.status == SubscriptionStatus.CANCELED.value
    assert updated_subscription.canceled_at is not None
    assert updated_subscription.end_date is not None


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_cancel_without_active_subscription(client, db, user_token, api_version):
    """Test canceling without an active subscription."""
    response = client.post(
        f'{api_version}/subscriptions/cancel',
        data=json.dumps({"at_period_end": True}),
        content_type='application/json',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    
    assert response.status_code == 404


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_get_subscription_history(client, db, user_token, api_version):
    """Test getting subscription history."""
    # Create a plan
    plan = SubscriptionPlan(
        name="History Test Plan",
        description="Plan for testing history",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Create multiple subscriptions with different statuses
    now = datetime.now(UTC)
    active_sub = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(days=10),
        current_period_start=now - timedelta(days=10),
        current_period_end=now + timedelta(days=20),
        payment_status=PaymentStatus.PAID.value
    )
    
    canceled_sub = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.CANCELED.value,
        start_date=now - timedelta(days=60),
        current_period_start=now - timedelta(days=60),
        current_period_end=now - timedelta(days=30),
        payment_status=PaymentStatus.PAID.value,
        canceled_at=now - timedelta(days=40),
        end_date=now - timedelta(days=30)
    )
    
    expired_sub = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.EXPIRED.value,
        start_date=now - timedelta(days=120),
        current_period_start=now - timedelta(days=120),
        current_period_end=now - timedelta(days=90),
        payment_status=PaymentStatus.PAID.value,
        end_date=now - timedelta(days=90)
    )
    
    db.session.add_all([active_sub, canceled_sub, expired_sub])
    db.session.commit()
    
    # Get all subscription history
    response = client.get(
        f'{api_version}/subscriptions/history',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['total'] == 3
    assert len(data['subscriptions']) == 3
    
    # Test filtering by status
    response = client.get(
        f'{api_version}/subscriptions/history?status=expired',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['total'] == 1
    assert data['subscriptions'][0]['status'] == SubscriptionStatus.EXPIRED.value
    
    # Test multiple status filtering
    response = client.get(
        f'{api_version}/subscriptions/history?status=active,canceled',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['total'] == 2
    
    # Test pagination
    response = client.get(
        f'{api_version}/subscriptions/history?per_page=1&page=2',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['total'] == 3
    assert len(data['subscriptions']) == 1
    assert data['page'] == 2
    assert data['pages'] == 3


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_get_active_subscription(client, db, user_token, api_version):
    """Test getting the user's active subscription."""
    # Create a plan
    plan = SubscriptionPlan(
        name="Active Plan",
        description="Plan for active subscription test",
        price=19.99
    )
    db.session.add(plan)
    db.session.commit()
    
    # Create an active subscription
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_token['user_id'],
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        start_date=now - timedelta(days=10),
        current_period_start=now - timedelta(days=10),
        current_period_end=now + timedelta(days=20),
        payment_status=PaymentStatus.PAID.value
    )
    db.session.add(subscription)
    db.session.commit()
    
    # Get the active subscription
    response = client.get(
        f'{api_version}/subscriptions/active',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == SubscriptionStatus.ACTIVE.value
    assert data['plan_id'] == plan.id
    assert data['user_id'] == user_token['user_id']
    
    # Check that plan details are included
    assert 'plan' in data
    assert data['plan']['name'] == "Active Plan"
    
    # Price is now consistently returned as a float
    assert data['plan']['price'] == 19.99


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v3"])
def test_get_active_subscription_not_found(client, db, user_token, api_version):
    """Test getting active subscription when user has none."""
    response = client.get(
        f'{api_version}/subscriptions/active',
        headers={"Authorization": f"Bearer {user_token['token']}"}
    )
    
    assert response.status_code == 404 