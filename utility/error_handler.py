"""
Error handling utilities for Lambda handlers.
"""
import traceback
from typing import Any, Dict

from utility.errors import ApiError
from utility.json_encoder import json_dumps_safe
from utility.logger import get_logger
from utility.response import format_response


_logger = get_logger(__name__)


def _add_cors_headers(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add CORS headers to error response.
    """
    headers = response.get("headers", {})
    headers.update({
        "Access-Control-Allow-Origin": "http://localhost:3000",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Credentials": "true",
    })
    response["headers"] = headers
    return response


def handle_error(error: Exception) -> Dict[str, Any]:
    """
    Convert exceptions into API Gateway friendly responses with CORS headers.
    """

    # Log full stack for debugging (kept server-side, not returned to client).
    # Using exception() ensures stack trace is emitted at ERROR level.
    _logger.exception("Unhandled error processing request", exc_info=error)
    # Fallback stdout to ensure visibility in logs even if logging is filtered.
    print("[ERROR] Unhandled exception:", repr(error))
    print("[ERROR] Traceback:", traceback.format_exc())

    if isinstance(error, ApiError):
        body = format_response(success=False, data=None, message=error.message, error={"code": error.error_code})
        status = error.status_code
    else:
        body = format_response(success=False, data=None, message="Internal server error", error={"code": "internal_error"})
        status = 500
    response = {"statusCode": status, "body": json_dumps_safe(body)}
    return _add_cors_headers(response)

