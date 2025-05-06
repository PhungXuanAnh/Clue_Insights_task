"""
Authentication namespace for handling user authentication (v1).
"""
from flask_restx import Namespace

auth_ns = Namespace(
    'auth', 
    description='Authentication operations'
)

from . import routes 