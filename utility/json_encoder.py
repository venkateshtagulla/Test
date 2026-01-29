"""
JSON serialization utilities for handling DynamoDB types and other non-serializable objects.
"""
import json
from decimal import Decimal
from typing import Any


class DecimalEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles DynamoDB Decimal types.
    Converts Decimal to float for JSON serialization.
    """

    def default(self, obj: Any) -> Any:
        """
        Convert Decimal to float for JSON serialization.
        """
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def json_dumps_safe(obj: Any, **kwargs: Any) -> str:
    """
    Safely serialize Python objects to JSON, handling DynamoDB types like Decimal.
    
    Args:
        obj: Object to serialize
        **kwargs: Additional arguments to pass to json.dumps
        
    Returns:
        JSON string representation of the object
    """
    return json.dumps(obj, cls=DecimalEncoder, **kwargs)

