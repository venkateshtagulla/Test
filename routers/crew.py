"""
Lambda handlers for crew management (admin side).
"""
import json
from base64 import b64decode
from typing import Any, Dict

from config.jwt_config import get_subject_from_access_token
from models.request.crew import AdminResetCrewPasswordRequest, CreateCrewRequest, CrewLoginRequest, CrewRegisterRequest, GetCrewRequest, ListCrewRequest
from repository.crew_repository import CrewRepository
from services.crew_service import CrewService
from services.dashboard_service import DashboardService
from services.sync_service import SyncService
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.errors import ApiError
from utility.body_parser import parse_json_body
from utility.json_encoder import json_dumps_safe
from utility.logger import get_logger
from utility.multipart_parser import parse_multipart_form_data
from utility.response import format_response


repository = CrewRepository()
service = CrewService(repository=repository)
dashboard_service = DashboardService()
sync_service = SyncService()
logger = get_logger(__name__)


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
def create_crew_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Create crew member.
    Supports both JSON and multipart/form-data (for file uploads).
    """

    try:
        admin_id = _get_admin_id_from_event(event)
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
            
            # Extract fields for request model
            payload_data = {
                "first_name": form_fields.get("first_name", ""),
                "last_name": form_fields.get("last_name", ""),
                "email": form_fields.get("email"),
                "phone_number": form_fields.get("phone_number"),
                "password": form_fields.get("password"),  # Optional password
                "role": form_fields.get("role"),
                "id_proof_url": form_fields.get("id_proof_url"),  # Optional if file is uploaded
                "address_proof_url": form_fields.get("address_proof_url"),  # Optional if file is uploaded
                "additional_docs": None,  # Will be handled via file uploads
            }
            
            payload = CreateCrewRequest(**payload_data)
            data = service.create_crew(admin_id, payload, files=files if files else None)
        else:
            # Standard JSON request
            body = _parse_body(event)
            payload = CreateCrewRequest(**body)
            data = service.create_crew(admin_id, payload)
        
        response = format_response(True, data, "Crew member created successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def get_crew_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Get crew member by id.
    """

    try:
        params = event.get("pathParameters") or {}
        payload = GetCrewRequest(**params)
        data = service.get_crew(payload)
        response = format_response(True, data, "Crew fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_crew_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List crew with pagination. Query params: page (default 1), limit (default 20, max 100).
    Requires admin bearer token.
    """

    try:
        _get_admin_id_from_event(event)  # auth check
        params = event.get("queryStringParameters") or {}

        page_raw = params.get("page") if isinstance(params, dict) else None
        limit_raw = params.get("limit") if isinstance(params, dict) else None

        payload = ListCrewRequest(
            page=int(page_raw) if page_raw is not None else 1,
            limit=int(limit_raw) if limit_raw is not None else 20,
        )

        data = service.list_crew(payload)
        response = format_response(True, data, "Crew fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def register_crew_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Register crew member API Gateway handler.
    """

    try:
        body = parse_json_body(event)
        payload = CrewRegisterRequest(**body)
        data = service.register_crew(payload)
        response = format_response(True, data, "Crew registered successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def login_crew_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Login crew member API Gateway handler.
    """

    try:
        body = parse_json_body(event)
        payload = CrewLoginRequest(**body)
        data = service.login_crew(payload)
        response = format_response(True, data, "Login successful")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def admin_reset_crew_password_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Admin reset crew password handler.
    """

    try:
        _get_admin_id_from_event(event)  # auth check
        body = _parse_body(event)
        params = event.get("pathParameters") or {}
        
        # Merge path parameter crew_id with body
        payload_data = {**body, "crew_id": params.get("crew_id")}
        if not payload_data.get("crew_id"):
            raise ApiError("crew_id is required in path", 400, "missing_crew_id")
        
        payload = AdminResetCrewPasswordRequest(**payload_data)
        data = service.reset_password(payload)
        response = format_response(True, data, "Crew password reset successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def admin_delete_crew_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Admin delete (soft delete) crew handler.
    """

    try:
        _get_admin_id_from_event(event)  # auth check
        params = event.get("pathParameters") or {}
        
        # Extract crew_id from path
        crew_id = params.get("crew_id")
        if not crew_id:
            raise ApiError("crew_id is required in path", 400, "missing_crew_id")
        
        from models.request.crew import AdminDeleteCrewRequest
        payload = AdminDeleteCrewRequest(crew_id=crew_id)
        data = service.delete_crew(payload)
        response = format_response(True, data, "Crew deleted successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def crew_me_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Auth-protected endpoint to fetch the currently authenticated crew profile.
    """

    try:
        headers = event.get("headers") or {}
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = auth_header.removeprefix("Bearer ").strip()
        crew_id = get_subject_from_access_token(token)
        data = service.get_profile_by_id(crew_id)
        response = format_response(True, data, "Current crew profile fetched")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)



@cors_middleware()
def crew_dashboard_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Auth-protected endpoint to fetch dashboard data for the authenticated crew member.
    """

    try:
        headers = event.get("headers") or {}
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = auth_header.removeprefix("Bearer ").strip()
        crew_id = get_subject_from_access_token(token)
        
        logger.info("Fetching dashboard for crew_id: %s", crew_id)
        
        data = dashboard_service.get_crew_dashboard(crew_id)
        response = format_response(True, data, "Crew dashboard fetched successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Error in crew_dashboard_handler: %s", exc, exc_info=True)
        return handle_error(exc)


@cors_middleware()
def crew_sync_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    POST endpoint to check sync status for the authenticated crew member.
    """

    try:
        headers = event.get("headers") or {}
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = auth_header.removeprefix("Bearer ").strip()
        crew_id = get_subject_from_access_token(token)
        
        logger.info("Checking sync status for crew_id: %s", crew_id)
        
        data = sync_service.get_sync_status(crew_id)
        response = format_response(True, data, "Sync status fetched successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Error in crew_sync_handler: %s", exc, exc_info=True)
        return handle_error(exc)

