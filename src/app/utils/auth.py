"""
Authentication utilities and decorators.
"""
from functools import wraps

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
            claims = get_jwt()
            is_admin = claims.get('is_admin', False)
            
            if not is_admin:
                return {"message": "Admin privileges required"}, 403
                
            return fn(*args, **kwargs)
        return decorator
    return wrapper 