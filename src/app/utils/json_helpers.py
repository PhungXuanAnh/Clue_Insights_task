"""
JSON utility functions for the API.
"""
import decimal
import json
from datetime import date, datetime


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that can handle Decimal, datetime, and date types.
    
    This encoder converts:
    - Decimal objects to float
    - datetime objects to ISO format strings
    - date objects to ISO format strings
    """
    
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super(CustomJSONEncoder, self).default(obj)


def convert_decimal_in_dict(obj):
    """
    Recursively convert Decimal types to float in dictionaries or lists.
    
    Args:
        obj: Dictionary, list, or scalar value to process
        
    Returns:
        Same structure with Decimal types converted to float
    """
    if isinstance(obj, dict):
        return {k: convert_decimal_in_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_in_dict(item) for item in obj]
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj 