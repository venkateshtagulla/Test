"""
Shared request body parsing utilities for Lambda handlers.
"""
from base64 import b64decode
from typing import Any, Dict

import json

from utility.errors import ApiError


def parse_json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and validate the JSON body from an API Gateway proxy event.

    This helper:
    - Supports both plain string and dict bodies
    - Decodes base64-encoded bodies when `isBase64Encoded` is true
    - Raises `ApiError` with safe, client-facing messages for all failures
    """

    raw_body = event.get("body")
    if raw_body is None:
        raise ApiError("Request body is required", 400, "missing_body")

    if isinstance(raw_body, dict):
        return raw_body

    if event.get("isBase64Encoded"):
        try:
            raw_body = b64decode(raw_body).decode("utf-8")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise ApiError("Invalid base64 body", 400, "invalid_base64_body") from exc

    if not isinstance(raw_body, str):
        raise ApiError("Invalid request body", 400, "invalid_body")

    try:
        raw_body = raw_body.strip()
        if not raw_body:
            raise ApiError("Request body is empty", 400, "empty_body")
        return json.loads(raw_body)
    except ApiError:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise ApiError("Malformed JSON body", 400, "invalid_json") from exc



