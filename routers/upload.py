"""
Lambda handler for generating S3 pre-signed upload URLs.
"""
import json
from base64 import b64decode
from typing import Any, Dict
from uuid import uuid4

from config.jwt_config import get_subject_from_access_token
from models.request.upload import PresignUploadRequest
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.errors import ApiError
from utility.response import format_response
from utility.s3_utils import generate_presigned_put_url


def _get_admin_id_from_event(event: Dict[str, Any]) -> str:
    """
    Extract admin id from Authorization Bearer token.
    """

    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()
    return get_subject_from_access_token(token)


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely parse the JSON body from an API Gateway event.
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


@cors_middleware()
def presign_upload_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Generate a pre-signed S3 upload URL.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        body = _parse_body(event)
        payload = PresignUploadRequest(**body)
        prefix = payload.folder.rstrip("/") if payload.folder else "uploads"
        key = f"{prefix}/{admin_id}/{uuid4()}_{payload.file_name}"
        presign = generate_presigned_put_url(key=key, content_type=payload.content_type)
        response = format_response(True, presign, "Upload URL generated")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)

