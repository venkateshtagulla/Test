"""
Lambda handlers for admin-managed inspectors.
"""
import json
from base64 import b64decode
from typing import Any, Dict

from config.jwt_config import get_subject_from_access_token
from models.request.admin_inspector import (
    AdminCreateInspectorRequest,
    AdminResetInspectorPasswordRequest,
    GetAdminInspectorRequest,
    ListAdminInspectorsRequest,
)
from repository.inspector_repository import InspectorRepository
from services.admin_inspector_service import AdminInspectorService
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.errors import ApiError
from utility.multipart_parser import parse_multipart_form_data
from utility.response import format_response


repository = InspectorRepository()
service = AdminInspectorService(repository=repository)


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
def admin_create_inspector_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Admin create inspector with documents and password.
    Supports both JSON and multipart/form-data (for file uploads).
    """

    try:
        admin_id=_get_admin_id_from_event(event)  # auth check
        # Get content type from headers (API Gateway may lowercase headers)
        headers = event.get("headers", {}) or {}
        content_type = (
            headers.get("Content-Type") or 
            headers.get("content-type") or 
            headers.get("Content-type") or
            ""
        )
        
        if "multipart/form-data" in content_type.lower():
            # Parse multipart form data
            form_fields, files = parse_multipart_form_data(event)

            # Defensive: ensure we actually parsed fields
            if not form_fields:
                raise ApiError(
                    "No form fields were parsed from multipart payload",
                    400,
                    "missing_form_fields",
                )

            # Extract fields for request model
            payload_data = {
                # Let Pydantic enforce required fields instead of
                # silently defaulting to empty strings (which would
                # cause DynamoDB ValidationException for GSI keys).
                "first_name": form_fields.get("first_name",""),
                "last_name": form_fields.get("last_name",""),
                "email": form_fields.get("email"),
                "phone_number": form_fields.get("phone_number"),
                "password": form_fields.get("password"),
                "role": form_fields.get("role"),
                "id_proof_url": form_fields.get("id_proof_url"),  # Optional if file is uploaded
                "address_proof_url": form_fields.get("address_proof_url"),  # Optional if file is uploaded
                "additional_docs": None,  # Will be handled via file uploads
            }

            # Surface a clear 400 if required fields are missing in multipart form
            '''missing_fields = [
                field
                for field in ("first_name", "last_name", "email", "password")
                if not payload_data.get(field)
            ]
            if missing_fields:
                raise ApiError(
                    f"Missing required form fields: {', '.join(missing_fields)}",
                    400,
                    "missing_form_fields",
                )'''
            print("DEBUG: Calling service now!") # Add this line
            payload = AdminCreateInspectorRequest(**payload_data)
            data = service.create_inspector(admin_id, payload, files=files if files else None)
        else:
            # Standard JSON request
            body = _parse_body(event)
            payload = AdminCreateInspectorRequest(**body)
            data = service.create_inspector(admin_id,payload.model_dump())
        
        response = format_response(True, data, "Inspector created successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def admin_get_inspector_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Admin get inspector by id.
    """

    try:
        _get_admin_id_from_event(event)  # auth check
        params = event.get("pathParameters") or {}
        payload = GetAdminInspectorRequest(**params)
        data = service.get_inspector(payload)
        response = format_response(True, data, "Inspector fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def admin_list_inspectors_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Admin list inspectors with pagination and signed document URLs.

    Query parameters:
      - page: int (1-based, default 1)
      - limit: int (default 20, max 100)
    """

    try:
        _get_admin_id_from_event(event)  # auth check
        params = event.get("queryStringParameters") or {}

        page_raw = params.get("page") if isinstance(params, dict) else None
        limit_raw = params.get("limit") if isinstance(params, dict) else None

        payload = ListAdminInspectorsRequest(
            page=int(page_raw) if page_raw is not None else 1,
            limit=int(limit_raw) if limit_raw is not None else 20,
        )

        data = service.list_inspectors(payload)
        response = format_response(True, data, "Inspectors fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def admin_reset_inspector_password_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Admin reset inspector password handler.
    """

    try:
        _get_admin_id_from_event(event)  # auth check
        body = _parse_body(event)
        params = event.get("pathParameters") or {}
        
        # Merge path parameter inspector_id with body
        payload_data = {**body, "inspector_id": params.get("inspector_id")}
        if not payload_data.get("inspector_id"):
            raise ApiError("inspector_id is required in path", 400, "missing_inspector_id")
        
        payload = AdminResetInspectorPasswordRequest(**payload_data)
        data = service.reset_password(payload)
        response = format_response(True, data, "Inspector password reset successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def admin_delete_inspector_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Admin delete (soft delete) inspector handler.
    """

    try:
        _get_admin_id_from_event(event)  # auth check
        params = event.get("pathParameters") or {}
        
        # Extract inspector_id from path
        inspector_id = params.get("inspector_id")
        if not inspector_id:
            raise ApiError("inspector_id is required in path", 400, "missing_inspector_id")
        
        from models.request.admin_inspector import AdminDeleteInspectorRequest
        payload = AdminDeleteInspectorRequest(inspector_id=inspector_id)
        data = service.delete_inspector(payload)
        response = format_response(True, data, "Inspector deleted successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)

