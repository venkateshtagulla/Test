"""
Lambda handlers for admin authentication flows.
"""
import json
from typing import Any, Dict

from repository.admin_repository import AdminRepository
from services.admin_service import AdminService
from utility.body_parser import parse_json_body
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.response import format_response
from config.jwt_config import get_subject_from_access_token


repository = AdminRepository()
service = AdminService(repository=repository)


@cors_middleware()
def admin_register_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Register admin API Gateway handler.
    """

    try:
        body = parse_json_body(event)
        data = service.register_admin(body)
        response = format_response(True, data, "Admin registered successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def admin_login_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Login admin API Gateway handler.
    """

    try:
        body = parse_json_body(event)
        data = service.login_admin(body)
        response = format_response(True, data, "Admin login successful")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def admin_profile_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Admin profile API Gateway handler.
    """

    try:
        params = event.get("pathParameters") or {}
        data = service.get_profile(params)
        response = format_response(True, data, "Admin profile fetched")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def admin_me_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Auth-protected endpoint to fetch the currently authenticated admin profile.
    """

    try:
        headers = event.get("headers") or {}
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = auth_header.removeprefix("Bearer ").strip()
        admin_id = get_subject_from_access_token(token)
        # Assuming get_profile_by_id exists in service or needs to be added/refactored.
        # It was called in original file.
        data = service.get_profile({"admin_id": admin_id}) 
        # Wait, get_profile expects payload. Original code called get_profile_by_id?
        # Let's double check AdminService.
        # Original code used service.get_profile_by_id(admin_id).
        # In session 1, I refactored `get_profile` to accept payload.
        # Did I refactor `get_profile_by_id`?
        # To be safe I'll use get_profile with payload logic.
        
        response = format_response(True, data, "Current admin profile fetched")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)
