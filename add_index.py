#!/usr/bin/env python
"""
Script to add the composite index for JOIN operations optimization.
"""
from sqlalchemy import text

from app import create_app, db

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # Check if index exists
        result = db.session.execute(
            text("SHOW INDEX FROM user_subscriptions WHERE Key_name = 'idx_user_subscriptions_plan_join'")
        ).fetchall()
        
        if not result:
            print("Creating index idx_user_subscriptions_plan_join...")
            db.session.execute(
                text("CREATE INDEX idx_user_subscriptions_plan_join ON user_subscriptions (user_id, plan_id, status)")
            )
            db.session.commit()
            print("Index created successfully.")
        else:
            print("Index already exists, no action needed.") 