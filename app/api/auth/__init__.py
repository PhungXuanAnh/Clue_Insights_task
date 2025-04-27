"""
Authentication namespace for handling user authentication.
"""
from flask_restx import Namespace

auth_ns = Namespace(
    'auth', 
    description='Authentication operations'
)

from . import routes 