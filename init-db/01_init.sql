-- Initial database setup script

-- Ensure we're using the right database
USE subscription_dev_db;

-- Create tables if they don't exist yet
-- Note: In real deployment, we'll use SQLAlchemy for migrations,
-- but this helps with initial Docker setup

-- Create indices for optimized queries
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

CREATE INDEX IF NOT EXISTS idx_subscription_plans_name ON subscription_plans(name);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_plan_id ON user_subscriptions(plan_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_dates ON user_subscriptions(start_date, end_date);

-- Composite indices for common query patterns
CREATE INDEX IF NOT EXISTS idx_user_active_subscription ON user_subscriptions(user_id, status, end_date); 