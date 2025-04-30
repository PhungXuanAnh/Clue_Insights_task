#!/usr/bin/env python
"""
Script to create an admin user for testing.
"""
from app import create_app, db
from app.models.user import User

app = create_app()

with app.app_context():
    # Check if admin user already exists
    admin = User.query.filter_by(username='admin').first()
    
    if not admin:
        # Create admin user with is_admin=True
        admin = User(username='admin', email='admin@example.com', password='admin123', is_admin=True)
        db.session.add(admin)
        db.session.commit()
        print(f'Admin user created with ID: {admin.id}')
    else:
        # Ensure existing admin user has admin privileges
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
            print(f'Updated user ID: {admin.id} with admin privileges')
        else:
            print(f'Admin user already exists with ID: {admin.id}') 