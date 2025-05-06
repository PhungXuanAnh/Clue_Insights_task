#!/usr/bin/env python
"""
Script to create 1 million demo users with various subscription scenarios:
- 250,000 users for each of the 5 subscription plans
- 200,000 users with subscriptions expiring soon
- 150,000 new users
- 100,000 recent cancellations
"""
import os
import random
import sys
from datetime import UTC, datetime, timedelta

from faker import Faker

from app import create_app, db
from app.models import SubscriptionPlan, SubscriptionStatus, User, UserSubscription
from app.models.user_subscription import PaymentStatus

# Initialize faker for generating realistic user data
fake = Faker()

# Total users to generate
TOTAL_USERS = 1_000_000

# Users per plan (5 plans x 200,000 = 1,000,000)
USERS_PER_PLAN = 250_000

# Special status counts
EXPIRING_SOON_COUNT = 200_000
NEW_USERS_COUNT = 150_000
RECENTLY_CANCELED_COUNT = 100_000

def create_users_data():
    """Create 1 million users with subscription data based on specified distributions."""
    print("Starting user data generation...")
    print(f"Target: {TOTAL_USERS} users with varied subscription data")
    
    # Get all subscription plans
    plans = SubscriptionPlan.query.all()
    if not plans or len(plans) < 5:
        print("Error: Required subscription plans not found. Run create_sample_plans.py first.")
        return
    
    # Create a plan lookup for easier reference
    plan_lookup = {plan.name: plan for plan in plans}
    
    # Make sure we have all the required plans
    required_plans = ["Free Plan", "Basic Plan", "Pro Plan", "Basic Plan (Annual)", "Pro Plan (Annual)"]
    for plan_name in required_plans:
        if plan_name not in plan_lookup:
            print(f"Error: Required plan '{plan_name}' not found.")
            return
    
    # Track progress
    batch_size = 1000
    total_created = 0
    
    # Set up counters for each plan and status type
    plan_counters = {plan_name: 0 for plan_name in required_plans}
    expiring_soon_count = 0
    new_users_count = 0
    recently_canceled_count = 0
    
    # Current time as reference point
    now = datetime.now(UTC)
    
    # Create users in batches for better performance
    for batch_num in range(1, (TOTAL_USERS // batch_size) + 1):
        user_batch = []
        subscription_batch = []
        
        for i in range(batch_size):
            # Generate unique user data
            username = fake.user_name() + f"_{total_created + i}"
            email = f"{username}@{fake.domain_name()}"
            password = fake.password(length=12)
            
            # Create user object
            user = User(
                username=username,
                email=email,
                password=password
            )
            user_batch.append(user)
        
        # Add users to database in one batch
        db.session.add_all(user_batch)
        db.session.flush()  # To get IDs without committing
        
        # Now create subscriptions for these users
        for user in user_batch:
            # Determine which plan to assign based on distribution targets
            available_plans = [plan_name for plan_name in required_plans 
                               if plan_counters[plan_name] < USERS_PER_PLAN]
            
            if not available_plans:
                # If we've hit all targets, just use any plan
                plan_name = random.choice(required_plans)
            else:
                plan_name = random.choice(available_plans)
                plan_counters[plan_name] += 1
            
            plan = plan_lookup[plan_name]
            
            # Determine subscription status and dates based on distribution requirements
            status = SubscriptionStatus.ACTIVE.value
            payment_status = PaymentStatus.PAID.value
            start_date = now - timedelta(days=random.randint(1, 365))
            
            # Calculate end date based on plan interval
            if plan.interval == "monthly":
                end_date = start_date + timedelta(days=30)
                current_period_end = start_date + timedelta(days=30)
            else:  # annual
                end_date = start_date + timedelta(days=365)
                current_period_end = start_date + timedelta(days=365)
            
            # Adjust for special status categories
            is_expiring_soon = False
            is_new_user = False
            is_recently_canceled = False
            canceled_at = None
            
            if expiring_soon_count < EXPIRING_SOON_COUNT:
                # Subscription expiring within 7 days
                is_expiring_soon = True
                current_period_end = now + timedelta(days=random.randint(1, 7))
                expiring_soon_count += 1
            elif new_users_count < NEW_USERS_COUNT:
                # New user (registered within last 7 days)
                is_new_user = True
                start_date = now - timedelta(days=random.randint(0, 7))
                if plan.interval == "monthly":
                    current_period_end = start_date + timedelta(days=30)
                else:
                    current_period_end = start_date + timedelta(days=365)
                new_users_count += 1
            elif recently_canceled_count < RECENTLY_CANCELED_COUNT:
                # Recently canceled subscription
                is_recently_canceled = True
                status = SubscriptionStatus.CANCELED.value
                canceled_at = now - timedelta(days=random.randint(1, 14))
                recently_canceled_count += 1
            
            # Create subscription
            subscription = UserSubscription(
                user_id=user.id,
                plan_id=plan.id,
                status=status,
                start_date=start_date,
                end_date=end_date if status == SubscriptionStatus.EXPIRED.value else None,
                current_period_start=start_date,
                current_period_end=current_period_end,
                payment_status=payment_status,
                canceled_at=canceled_at,
                auto_renew=not is_recently_canceled
            )
            
            subscription_batch.append(subscription)
        
        # Add subscriptions to database
        db.session.add_all(subscription_batch)
        
        # Commit the batch
        db.session.commit()
        
        # Update progress
        total_created += len(user_batch)
        progress = (total_created / TOTAL_USERS) * 100
        print(f"Progress: {progress:.2f}% - Created {total_created} users")
    
    # Print summary
    print("\nUser generation complete!")
    print(f"Total users created: {total_created}")
    print("\nDistribution by plan:")
    for plan_name, count in plan_counters.items():
        print(f"- {plan_name}: {count} users")
    
    print("\nSpecial categories:")
    print(f"- Subscriptions expiring soon: {expiring_soon_count}")
    print(f"- New users (last 7 days): {new_users_count}")
    print(f"- Recently canceled: {recently_canceled_count}")


if __name__ == "__main__":
    try:
        # Add faker to requirements if not present
        print("Checking for required package (faker)...")
        try:
            import faker
        except ImportError:
            print("Package 'faker' not found. Please install it using:")
            print("pip install faker")
            sys.exit(1)
        
        # Create the Flask app with the development configuration
        app = create_app('development')
        
        # Push an application context
        with app.app_context():
            create_users_data()
            
        print("User data generation completed successfully.")
        sys.exit(0)
    except Exception as e:
        print(f"Error creating user data: {str(e)}")
        sys.exit(1)
