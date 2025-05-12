#!/usr/bin/env python
import os
import sys

from app import create_app, db
from app.models import SubscriptionPlan


def create_sample_plans():
    """Create sample subscription plans if they don't already exist."""
    print("Checking for existing plans...")
    
    existing_plans = SubscriptionPlan.query.filter(
        SubscriptionPlan.name.in_(["Free Plan", "Basic Plan", "Pro Plan", "Basic Plan (Annual)", "Pro Plan (Annual)"])
    ).all()
    
    existing_plan_names = [plan.name for plan in existing_plans]
    print(f"Found existing plans: {existing_plan_names}")
    
    plans_to_create = []
    
    if "Free Plan" not in existing_plan_names:
        free_plan = SubscriptionPlan(
            name="Free Plan",
            description="Free tier with basic features",
            price=0.00,
            interval="monthly",
            duration_months=1,
            features={
                "storage": 1,     # 1 GB storage
                "projects": 1,    # 1 project
                "users": 1        # 1 user
            },
            status="active",
            is_public=True
        )
        plans_to_create.append(free_plan)
    
    # Basic Plan
    if "Basic Plan" not in existing_plan_names:
        basic_plan = SubscriptionPlan(
            name="Basic Plan",
            description="Standard subscription with more features",
            price=9.99,
            interval="monthly",
            duration_months=1,
            features={
                "storage": 10,    # 10 GB storage
                "projects": 5,    # 5 projects
                "users": 3        # 3 users
            },
            status="active",
            is_public=True
        )
        plans_to_create.append(basic_plan)
    
    # Pro Plan
    if "Pro Plan" not in existing_plan_names:
        pro_plan = SubscriptionPlan(
            name="Pro Plan",
            description="Premium subscription with all features",
            price=29.99,
            interval="monthly",
            duration_months=1,
            features={
                "storage": 50,    # 50 GB storage
                "projects": 20,   # 20 projects
                "users": 10       # 10 users
            },
            status="active",
            is_public=True
        )
        plans_to_create.append(pro_plan)
    
    # Create annual variants for Basic and Pro
    if "Basic Plan (Annual)" not in existing_plan_names:
        basic_annual = SubscriptionPlan(
            name="Basic Plan (Annual)",
            description="Standard subscription with more features (annual billing)",
            price=99.99,  # ~17% discount vs monthly
            interval="annual",
            duration_months=12,
            features={
                "storage": 10,
                "projects": 5,
                "users": 3
            },
            status="active",
            is_public=True
        )
        plans_to_create.append(basic_annual)
    
    if "Pro Plan (Annual)" not in existing_plan_names:
        pro_annual = SubscriptionPlan(
            name="Pro Plan (Annual)",
            description="Premium subscription with all features (annual billing)",
            price=299.99,  # ~17% discount vs monthly
            interval="annual",
            duration_months=12,
            features={
                "storage": 50,
                "projects": 20,
                "users": 10
            },
            status="active",
            is_public=True
        )
        plans_to_create.append(pro_annual)
    
    # Add all plans to the database
    if plans_to_create:
        try:
            for plan in plans_to_create:
                db.session.add(plan)
            db.session.commit()
            
            print(f"Successfully created {len(plans_to_create)} new plans:")
            for plan in plans_to_create:
                print(f"- {plan.name} ({plan.interval}, ${plan.price})")
        except Exception as e:
            db.session.rollback()
            raise e
    else:
        print("No new plans needed to be created.")

if __name__ == "__main__":
    try:
        app = create_app('development')
        with app.app_context():
            create_sample_plans()
            
        print("Sample plans creation completed successfully.")
        sys.exit(0)
    except Exception as e:
        print(f"Error creating sample plans: {str(e)}")
        sys.exit(1) 