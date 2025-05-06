#!/usr/bin/env python
"""
Main application entry point for Subscription Management API.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000) 