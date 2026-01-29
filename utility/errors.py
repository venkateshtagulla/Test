"""
Custom error definitions.
"""
from typing import Optional


class ApiError(Exception):
    """
    Represents a safe-to-return API error.
    """

    def __init__(self, message: str, status_code: int = 400, error_code: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

