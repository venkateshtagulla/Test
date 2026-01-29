"""
Lambda handlers for inspector authentication flows.
"""
import json
from typing import Any, Dict

from config.jwt_config import decode_access_token, get_subject_from_access_token
from repository.inspector_repository import InspectorRepository
from services.dashboard_service import DashboardService
from services.inspector_service import InspectorService
from services.sync_service import SyncService
from utility.body_parser import parse_json_body
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.json_encoder import json_dumps_safe
from utility.logger import get_logger
from utility.response import format_response


repository = InspectorRepository()
service = InspectorService(repository=repository)
dashboard_service = DashboardService()
sync_service = SyncService()
logger = get_logger(__name__)


@cors_middleware()
def register_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Register inspector API Gateway handler.
    """

    try:
        body = parse_json_body(event)
        # Manual validation or trust service to validate
        # Service now expects a dict and optionally validates
        data = service.register_inspector(body)
        response = format_response(True, data, "Inspector registered successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def login_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Login inspector API Gateway handler.
    """

    try:
        body = parse_json_body(event)
        data = service.login_inspector(body)
        response = format_response(True, data, "Login successful")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def profile_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Inspector profile API Gateway handler.
    """

    try:
        params = event.get("pathParameters") or {}
        data = service.get_profile(params)
        response = format_response(True, data, "Inspector profile fetched")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def inspector_me_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Auth-protected endpoint to fetch the currently authenticated inspector profile.
    """

    try:
        headers = event.get("headers") or {}
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = auth_header.removeprefix("Bearer ").strip()
        
        # Decode token to get full payload for logging
        token_payload = decode_access_token(token)
        inspector_id = token_payload.get("sub")
        email = token_payload.get("email")
        
        logger.info(
            "Inspector /me request - inspector_id: %s, email: %s",
            inspector_id,
            email,
        )
        
        if not inspector_id:
            raise ValueError("Invalid token: missing subject")
        
        data = service.get_profile_by_id(str(inspector_id), email=email)
        response = format_response(True, data, "Current inspector profile fetched")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Error in inspector_me_handler: %s", exc, exc_info=True)
        return handle_error(exc)


@cors_middleware()
def inspector_dashboard_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Auth-protected endpoint to fetch dashboard data for the authenticated inspector.
    """

    try:
        headers = event.get("headers") or {}
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = auth_header.removeprefix("Bearer ").strip()
        inspector_id = get_subject_from_access_token(token)
        
        logger.info("Fetching dashboard for inspector_id: %s", inspector_id)
        
        data = dashboard_service.get_inspector_dashboard(inspector_id)
        response = format_response(True, data, "Inspector dashboard fetched successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Error in inspector_dashboard_handler: %s", exc, exc_info=True)
        return handle_error(exc)


@cors_middleware()
def inspector_sync_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    POST endpoint to check sync status for the authenticated inspector.
    """

    try:
        headers = event.get("headers") or {}
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = auth_header.removeprefix("Bearer ").strip()
        inspector_id = get_subject_from_access_token(token)
        
        logger.info("Checking sync status for inspector_id: %s", inspector_id)
        
        data = sync_service.get_sync_status(inspector_id)
        response = format_response(True, data, "Sync status fetched successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Error in inspector_sync_handler: %s", exc, exc_info=True)
        return handle_error(exc)
