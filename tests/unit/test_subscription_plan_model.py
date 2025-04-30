"""
Unit tests for SubscriptionPlan model.
"""
import json
import pytest
from app.models.subscription_plan import SubscriptionPlan, SubscriptionInterval, PlanStatus

def test_subscription_plan_creation_with_default_values(db):
    """Test creating a subscription plan with default values."""
    plan = SubscriptionPlan(
        name="Basic Plan",
        description="Basic subscription plan",
        price=9.99
    )
    db.session.add(plan)
    db.session.commit()
    
    saved_plan = SubscriptionPlan.query.filter_by(name="Basic Plan").first()
    
    assert saved_plan is not None
    assert saved_plan.name == "Basic Plan"
    assert float(saved_plan.price) == 9.99
    assert saved_plan.description == "Basic subscription plan"
    assert saved_plan.interval == SubscriptionInterval.MONTHLY.value
    assert saved_plan.duration_months == 1
    assert saved_plan.status == PlanStatus.ACTIVE.value
    assert saved_plan.is_public is True
    assert saved_plan.max_users is None
    assert saved_plan.parent_id is None
    assert saved_plan.sort_order == 0

def test_subscription_plan_creation_with_custom_values(db):
    """Test creating a subscription plan with custom values."""
    features = {"feature1": True, "feature2": False, "custom_limit": 100}
    
    plan = SubscriptionPlan(
        name="Premium Plan",
        description="Premium subscription plan",
        price=29.99,
        interval=SubscriptionInterval.ANNUAL.value,
        duration_months=12,
        features=features,
        status=PlanStatus.ACTIVE.value,
        is_public=False,
        max_users=5,
        sort_order=10
    )
    db.session.add(plan)
    db.session.commit()
    
    saved_plan = SubscriptionPlan.query.filter_by(name="Premium Plan").first()
    
    assert saved_plan is not None
    assert saved_plan.name == "Premium Plan"
    assert float(saved_plan.price) == 29.99
    assert saved_plan.interval == SubscriptionInterval.ANNUAL.value
    assert saved_plan.duration_months == 12
    assert saved_plan.is_public is False
    assert saved_plan.max_users == 5
    assert saved_plan.sort_order == 10
    
    # Test features are saved correctly
    plan_features = saved_plan.get_features_dict()
    assert plan_features["feature1"] is True
    assert plan_features["feature2"] is False
    assert plan_features["custom_limit"] == 100

def test_subscription_plan_parent_child_relationship(db):
    """Test parent-child relationship between subscription plans."""
    parent_plan = SubscriptionPlan(
        name="Team Plan",
        description="Team subscription plan",
        price=49.99
    )
    db.session.add(parent_plan)
    db.session.flush()  # Flush to get the parent_id
    
    child_plan = SubscriptionPlan(
        name="Team Plus Plan",
        description="Enhanced team subscription plan",
        price=79.99,
        parent_id=parent_plan.id
    )
    db.session.add(child_plan)
    db.session.commit()
    
    # Refresh parent plan to load relationships
    db.session.refresh(parent_plan)
    
    # Check parent-child relationship
    assert len(parent_plan.child_plans) == 1
    assert parent_plan.child_plans[0].name == "Team Plus Plan"
    assert child_plan.parent.name == "Team Plan"

def test_subscription_plan_monthly_price_calculation(db):
    """Test monthly price calculation for different intervals."""
    monthly_plan = SubscriptionPlan(
        name="Monthly Plan",
        description="Monthly billing",
        price=10.0,
        interval=SubscriptionInterval.MONTHLY.value,
        duration_months=1
    )
    
    annual_plan = SubscriptionPlan(
        name="Annual Plan",
        description="Annual billing",
        price=96.0,
        interval=SubscriptionInterval.ANNUAL.value,
        duration_months=12
    )
    
    db.session.add_all([monthly_plan, annual_plan])
    db.session.commit()
    
    assert monthly_plan.monthly_price == 10.0
    assert annual_plan.monthly_price == 8.0  # 96 / 12 = 8

def test_subscription_plan_has_feature(db):
    """Test has_feature method to check feature existence."""
    features = {
        "unlimited_storage": True,
        "max_projects": 10,
        "custom_domain": False
    }
    
    plan = SubscriptionPlan(
        name="Feature Test Plan",
        description="Test features",
        price=19.99,
        features=features
    )
    db.session.add(plan)
    db.session.commit()
    
    assert plan.has_feature("unlimited_storage") is True
    assert plan.has_feature("custom_domain") is False
    assert plan.has_feature("nonexistent_feature") is False

def test_subscription_plan_unique_name_per_interval(db):
    """Test that plan names must be unique within an interval."""
    plan1 = SubscriptionPlan(
        name="Basic Plan",
        description="Monthly basic plan",
        price=9.99,
        interval=SubscriptionInterval.MONTHLY.value
    )
    db.session.add(plan1)
    db.session.commit()
    
    # Same name but different interval should work
    plan2 = SubscriptionPlan(
        name="Basic Plan",
        description="Annual basic plan",
        price=99.99,
        interval=SubscriptionInterval.ANNUAL.value
    )
    db.session.add(plan2)
    db.session.commit()
    
    # Same name and interval should fail
    plan3 = SubscriptionPlan(
        name="Basic Plan",
        description="Another monthly basic plan",
        price=19.99,
        interval=SubscriptionInterval.MONTHLY.value
    )
    db.session.add(plan3)
    
    with pytest.raises(Exception):  # Should raise an integrity error
        db.session.commit() 