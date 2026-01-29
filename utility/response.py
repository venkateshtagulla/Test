"""
Common response helpers.
"""
from typing import Any, Dict, Optional


def format_response(success: bool, data: Optional[Dict[str, Any]], message: str, error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Standard API response payload.
    """

    return {
        "success": success,
        "data": data or {},
        "message": message,
        "error": error,
    }

