"""
Integration tests for subscription plan API endpoints.
"""
# Standard library imports
import json

# Third-party imports
import pytest
from flask_jwt_extended import create_access_token

# Application imports
from app.models.subscription_plan import (
    PlanStatus,
    SubscriptionInterval,
    SubscriptionPlan,
)


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v2"])
def test_get_subscription_plans(client, db, api_version):
    """Test retrieving subscription plans."""
    # Create some test plans
    plan1 = SubscriptionPlan(
        name="Basic Plan", description="Basic plan for testing", price=9.99
    )
    plan2 = SubscriptionPlan(
        name="Premium Plan", description="Premium plan for testing", price=19.99
    )
    db.session.add_all([plan1, plan2])
    db.session.commit()

    # Make request to get plans
    response = client.get(f"{api_version}/plans/")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["total"] == 2
    assert len(data["plans"]) == 2
    assert data["plans"][0]["name"] == "Basic Plan"
    assert data["plans"][1]["name"] == "Premium Plan"


def test_get_subscription_plan_by_id(client, db):
    """Test retrieving a single subscription plan by ID."""
    # Create a test plan
    plan = SubscriptionPlan(
        name="Test Plan", description="Test plan for retrieval", price=29.99
    )
    db.session.add(plan)
    db.session.commit()

    # Make request to get the plan
    response = client.get(f"/api/v1/plans/{plan.id}")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["name"] == "Test Plan"
    assert float(data["price"]) == 29.99


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v2"])
def test_get_nonexistent_plan(client, api_version):
    """Test retrieving a plan that doesn't exist."""
    response = client.get(f"{api_version}/plans/9999")
    assert response.status_code == 404


def test_create_subscription_plan_with_auth(client, db, admin_token):
    """Test creating a subscription plan with authentication."""
    plan_data = {
        "name": "New Plan",
        "description": "New plan via API",
        "price": 39.99,
        "interval": SubscriptionInterval.MONTHLY.value,
        "features": {"feature1": True, "feature2": 100},
    }

    response = client.post(
        "/api/v1/plans/",
        data=json.dumps(plan_data),
        content_type="application/json",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    data = json.loads(response.data)

    print(f"Response data: {data}")

    assert response.status_code == 201
    assert data["name"] == "New Plan"
    assert float(data["price"]) == 39.99

    # Verify in database
    plan = SubscriptionPlan.query.filter_by(name="New Plan").first()
    assert plan is not None
    assert plan.get_features_dict()["feature1"] is True
    assert plan.get_features_dict()["feature2"] == 100


def test_create_subscription_plan_without_auth(client):
    """Test creating a subscription plan without authentication."""
    plan_data = {
        "name": "Unauthorized Plan",
        "description": "Should not be created",
        "price": 9.99,
    }

    response = client.post(
        "/api/v1/plans/", data=json.dumps(plan_data), content_type="application/json"
    )

    assert response.status_code == 401


def test_update_subscription_plan(client, db, admin_token):
    """Test updating a subscription plan."""
    # Create a plan to update
    plan = SubscriptionPlan(
        name="Plan to Update", description="Original description", price=49.99
    )
    db.session.add(plan)
    db.session.commit()

    update_data = {
        "name": "Updated Plan",
        "description": "Updated description",
        "price": 59.99,
        "features": {"new_feature": True},
    }

    response = client.put(
        f"/api/v1/plans/{plan.id}",
        data=json.dumps(update_data),
        content_type="application/json",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["name"] == "Updated Plan"
    assert data["description"] == "Updated description"
    assert float(data["price"]) == 59.99

    # Verify updates in database
    updated_plan = SubscriptionPlan.query.get(plan.id)
    assert updated_plan.name == "Updated Plan"
    assert updated_plan.description == "Updated description"
    assert float(updated_plan.price) == 59.99
    assert updated_plan.has_feature("new_feature") is True


def test_delete_subscription_plan(client, db, admin_token):
    """Test deleting a subscription plan."""
    # Create a plan to delete
    plan = SubscriptionPlan(
        name="Plan to Delete", description="Will be deleted", price=29.99
    )
    db.session.add(plan)
    db.session.commit()
    plan_id = plan.id

    response = client.delete(
        f"/api/v1/plans/{plan_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 204

    # Verify it's gone from the database
    deleted_plan = SubscriptionPlan.query.get(plan_id)
    assert deleted_plan is None


def test_get_intervals(client):
    """Test getting all subscription intervals."""
    response = client.get("/api/v1/plans/intervals")
    data = json.loads(response.data)

    assert response.status_code == 200
    # Check for all enum values
    interval_values = [i.value for i in SubscriptionInterval]
    result_values = [i["value"] for i in data]

    for value in interval_values:
        assert value in result_values


def test_get_plan_statuses(client):
    """Test getting all plan status options."""
    response = client.get("/api/v1/plans/statuses")
    data = json.loads(response.data)

    assert response.status_code == 200
    # Check for all enum values
    status_values = [s.value for s in PlanStatus]
    result_values = [s["value"] for s in data]

    for value in status_values:
        assert value in result_values


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v2"])
def test_filtering_plans_by_status(client, db, api_version):
    """Test filtering plans by status."""
    # Create plans with different statuses
    active_plan = SubscriptionPlan(
        name="Active Plan",
        description="Active plan for testing",
        price=9.99,
        status=PlanStatus.ACTIVE.value,
    )
    inactive_plan = SubscriptionPlan(
        name="Inactive Plan",
        description="Inactive plan for testing",
        price=19.99,
        status=PlanStatus.INACTIVE.value,
    )
    db.session.add_all([active_plan, inactive_plan])
    db.session.commit()

    # Test filtering by active status
    response = client.get(f"{api_version}/plans/?status=active")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["total"] == 1
    assert data["plans"][0]["name"] == "Active Plan"

    # Test filtering by inactive status
    response = client.get(f"{api_version}/plans/?status=inactive")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["total"] == 1
    assert data["plans"][0]["name"] == "Inactive Plan"


def test_public_and_non_public_plans(client, db):
    """Test filtering between public and non-public plans."""
    # Create public and non-public plans
    public_plan = SubscriptionPlan(
        name="Public Plan",
        description="Public plan for testing",
        price=9.99,
        is_public=True,
    )
    private_plan = SubscriptionPlan(
        name="Private Plan",
        description="Non-public plan for testing",
        price=19.99,
        is_public=False,
    )
    db.session.add_all([public_plan, private_plan])
    db.session.commit()

    # Test filtering to show only public plans (default)
    response = client.get("/api/v1/plans/")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["total"] == 1
    assert data["plans"][0]["name"] == "Public Plan"

    # Test showing all plans
    response = client.get("/api/v1/plans/?public_only=false")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["total"] == 2

    # Check plan names in results (order might vary)
    plan_names = [p["name"] for p in data["plans"]]
    assert "Public Plan" in plan_names
    assert "Private Plan" in plan_names


@pytest.mark.parametrize("api_version", ["/api/v1", "/api/v2"])
def test_pagination(client, db, api_version):
    """Test pagination of subscription plans."""
    # Create multiple plans
    for i in range(15):
        plan = SubscriptionPlan(
            name=f"Plan {i+1}",
            description=f"Test plan {i+1}",
            price=10.00 + i,
            sort_order=i,
        )
        db.session.add(plan)
    db.session.commit()

    # Test first page with 5 items per page
    response = client.get(f"{api_version}/plans/?per_page=5&page=1")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["total"] == 15
    assert data["page"] == 1
    assert data["per_page"] == 5
    assert data["pages"] == 3
    assert len(data["plans"]) == 5

    # Test second page
    response = client.get(f"{api_version}/plans/?per_page=5&page=2")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["page"] == 2
    assert len(data["plans"]) == 5

    # Test last page
    response = client.get(f"{api_version}/plans/?per_page=5&page=3")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data["page"] == 3
    assert len(data["plans"]) == 5


@pytest.fixture
def admin_token(app):
    """Create a test admin user and generate an access token."""
    with app.app_context():
        from app import db
        from app.models.user import User

        # Create test admin user
        admin = User(
            username="testadmin",
            email="admin@example.com",
            password="password123",
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()

        # Create access token with is_admin claim
        access_token = create_access_token(
            identity=str(admin.id), additional_claims={"is_admin": True}
        )

        return access_token
