"""Merged all migrations into a single file

Revision ID: init_tables
Revises: 
Create Date: 2024-05-05 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = 'init_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('subscription_plans',
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('features', sa.Text(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('interval', sa.String(length=20), nullable=False),
        sa.Column('duration_months', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('users',
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for subscription_plans
    with op.batch_alter_table('subscription_plans', schema=None) as batch_op:
        batch_op.create_index('idx_subscription_plan_parent', ['parent_id'], unique=False)
        batch_op.create_index('idx_subscription_plan_price', ['price'], unique=False)
        batch_op.create_index('idx_subscription_plan_public', ['is_public'], unique=False)
        batch_op.create_index('idx_subscription_plan_sort', ['sort_order'], unique=False)
        batch_op.create_index('idx_subscription_plan_status', ['status'], unique=False)
        batch_op.create_unique_constraint('uix_plan_name_interval', ['name', 'interval'])
        batch_op.create_foreign_key(None, 'subscription_plans', ['parent_id'], ['id'])

    # Create indices for users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)

    # Create token_blacklist table
    op.create_table('token_blacklist',
        sa.Column('jti', sa.String(length=36), nullable=False),
        sa.Column('token_type', sa.String(length=10), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('token_blacklist', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_token_blacklist_jti'), ['jti'], unique=True)

    # Create user_subscriptions table
    op.create_table('user_subscriptions',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('trial_end_date', sa.DateTime(), nullable=True),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('payment_status', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
        sa.Column('auto_renew', sa.Boolean(), nullable=False),
        sa.Column('subscription_metadata', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for user_subscriptions
    with op.batch_alter_table('user_subscriptions', schema=None) as batch_op:
        batch_op.create_index('idx_user_active_subscriptions', ['user_id', 'status'], unique=False)
        batch_op.create_index('idx_user_plan_subscription', ['user_id', 'plan_id'], unique=False)
        batch_op.create_index('idx_user_subscription_end_date', ['end_date'], unique=False)
        batch_op.create_index('idx_user_subscription_cancel_period_end', ['cancel_at_period_end', 'current_period_end'], unique=False)
        batch_op.create_index('idx_user_subscription_current_period', ['current_period_start', 'current_period_end'], unique=False)
        batch_op.create_index('idx_user_subscription_payment', ['payment_status'], unique=False)
        batch_op.create_index('idx_user_subscription_status_period_end', ['status', 'current_period_end'], unique=False)
        batch_op.create_index('idx_user_subscription_user_status', ['user_id', 'status'], unique=False)
        batch_op.create_index('idx_user_subscriptions_plan_join', ['user_id', 'plan_id', 'status'], unique=False)
        batch_op.create_index('idx_user_subscriptions_status_current_period_end', ['status', 'current_period_end'], unique=False)
        batch_op.create_index('idx_user_subscriptions_status_end_date', ['status', 'end_date'], unique=False)
        batch_op.create_index('idx_user_subscriptions_user_id_status', ['user_id', 'status'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # Drop user_subscriptions and all its indices
    with op.batch_alter_table('user_subscriptions', schema=None) as batch_op:
        batch_op.drop_index('idx_user_subscriptions_user_id_status')
        batch_op.drop_index('idx_user_subscriptions_status_end_date')
        batch_op.drop_index('idx_user_subscriptions_status_current_period_end')
        batch_op.drop_index('idx_user_subscriptions_plan_join')
        batch_op.drop_index('idx_user_subscription_user_status')
        batch_op.drop_index('idx_user_subscription_status_period_end')
        batch_op.drop_index('idx_user_subscription_payment')
        batch_op.drop_index('idx_user_subscription_current_period')
        batch_op.drop_index('idx_user_subscription_cancel_period_end')
        batch_op.drop_index('idx_user_subscription_end_date')
        batch_op.drop_index('idx_user_plan_subscription')
        batch_op.drop_index('idx_user_active_subscriptions')

    op.drop_table('user_subscriptions')
    
    # Drop token_blacklist
    with op.batch_alter_table('token_blacklist', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_token_blacklist_jti'))

    op.drop_table('token_blacklist')
    
    # Drop users and its indices
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_username'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    
    # Drop subscription_plans and its indices
    with op.batch_alter_table('subscription_plans', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint('uix_plan_name_interval', type_='unique')
        batch_op.drop_index('idx_subscription_plan_status')
        batch_op.drop_index('idx_subscription_plan_sort')
        batch_op.drop_index('idx_subscription_plan_public')
        batch_op.drop_index('idx_subscription_plan_price')
        batch_op.drop_index('idx_subscription_plan_parent')

    op.drop_table('subscription_plans')
    # ### end Alembic commands ###