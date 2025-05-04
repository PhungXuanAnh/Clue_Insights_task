"""Add missing indexes for common queries

Revision ID: 045444694e5d
Revises: merged_migration
Create Date: 2025-05-04 10:07:12.760176

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '045444694e5d'
down_revision = 'merged_migration'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing index on token_blacklist.expires_at
    # This helps with token cleanup operations and expired token queries
    with op.batch_alter_table('token_blacklist', schema=None) as batch_op:
        batch_op.create_index('idx_token_blacklist_expires_at', ['expires_at'], unique=False)
    
    # Add missing indexes on subscription_plans
    with op.batch_alter_table('subscription_plans', schema=None) as batch_op:
        # Add indexes for plan filtering by interval and duration
        batch_op.create_index('idx_subscription_plan_interval', ['interval'], unique=False)
        batch_op.create_index('idx_subscription_plan_duration', ['duration_months'], unique=False)
        
        # Add composite index for interval+status for optimized active plan queries
        batch_op.create_index('idx_subscription_plan_interval_status', ['interval', 'status'], unique=False)

    # Add missing indexes on user_subscriptions
    with op.batch_alter_table('user_subscriptions', schema=None) as batch_op:
        # Add index for canceled_at for better cancellation reporting
        batch_op.create_index('idx_user_subscription_canceled_at', ['canceled_at'], unique=False)
        
        # Add composite index for user_id+plan_id for faster lookups of specific user-plan combinations
        # This is used heavily in subscription change operations
        # Check if it doesn't already exist as idx_user_plan_subscription
        try:
            batch_op.create_index('idx_user_subscription_user_plan', ['user_id', 'plan_id'], unique=False)
        except:
            # Index might already exist with a different name
            pass
        
        # Add composite indexes for expiring subscriptions queries
        # Check if it doesn't already exist as idx_user_subscriptions_status_end_date
        try:
            batch_op.create_index(
                'idx_user_subscription_status_end_date', 
                ['status', 'end_date'], 
                unique=False
            )
        except:
            # Index might already exist with a different name
            pass
        
        # Add optimized indexes for the active subscription query in sql_optimizations.py
        batch_op.create_index(
            'idx_user_subscription_active_dates',
            ['user_id', 'status', 'start_date', 'end_date'],
            unique=False
        )
        
        # Add index for trial subscriptions query
        batch_op.create_index(
            'idx_user_subscription_user_trial',
            ['user_id', 'status', 'trial_end_date'],
            unique=False
        )


def downgrade():
    # Remove added indexes from user_subscriptions
    with op.batch_alter_table('user_subscriptions', schema=None) as batch_op:
        batch_op.drop_index('idx_user_subscription_user_trial')
        batch_op.drop_index('idx_user_subscription_active_dates')
        
        # Try to drop indexes that might have been skipped in upgrade if they already existed
        try:
            batch_op.drop_index('idx_user_subscription_status_end_date')
        except:
            pass
            
        try:
            batch_op.drop_index('idx_user_subscription_user_plan')
        except:
            pass
            
        batch_op.drop_index('idx_user_subscription_canceled_at')
    
    # Remove added indexes from subscription_plans
    with op.batch_alter_table('subscription_plans', schema=None) as batch_op:
        batch_op.drop_index('idx_subscription_plan_interval_status')
        batch_op.drop_index('idx_subscription_plan_duration')
        batch_op.drop_index('idx_subscription_plan_interval')
    
    # Remove added index from token_blacklist
    with op.batch_alter_table('token_blacklist', schema=None) as batch_op:
        batch_op.drop_index('idx_token_blacklist_expires_at')
