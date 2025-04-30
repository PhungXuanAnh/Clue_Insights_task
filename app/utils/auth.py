"""
Authentication utilities and decorators.
"""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt


def admin_required():
    """
    Decorator to check if the current user has admin privileges.
    Must be used after jwt_required() decorator.
    
    Returns:
        function: Decorator function
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            # Get JWT claims directly from the token
            claims = get_jwt()
            
            # Check for admin privileges in the additional claims
            is_admin = claims.get('is_admin', False)
            
            if not is_admin:
                return {"message": "Admin privileges required"}, 403
                
            return fn(*args, **kwargs)
        return decorator
    return wrapper 