"""
Lambda handlers for vessel management (admin-owned vessels).
"""
import json
from typing import Any, Dict

from config.jwt_config import get_subject_from_access_token
from models.request.vessel import (
    CreateVesselRequest,
    GetVesselRequest,
    ListVesselsRequest,
)
from models.request.vessel_assignment import (
    CreateVesselAssignmentRequest,
    GetVesselAssignmentsRequest,
)
from repository.vessel_repository import VesselRepository
from services.vessel_assignment_service import VesselAssignmentService
from services.vessel_service import VesselService
from utility.body_parser import parse_json_body
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.json_encoder import json_dumps_safe
from utility.response import format_response


repository = VesselRepository()
service = VesselService(repository=repository)
vessel_assignment_service = VesselAssignmentService()


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


@cors_middleware()
def create_vessel_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Create vessel API Gateway handler (admin must be authenticated).
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        body = parse_json_body(event)
        payload = CreateVesselRequest(**body)
        data = service.create_vessel(admin_id, payload)
        response = format_response(True, data, "Vessel created successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_vessels_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List vessels for logged-in admin with pagination.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        query_params = event.get("queryStringParameters") or {}
        payload = ListVesselsRequest(
            page=int(query_params.get("page", 1)),
            limit=int(query_params.get("limit", 20)),
        )
        data = service.list_vessels(admin_id, payload)
        response = format_response(True, data, "Vessels fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def get_vessel_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Get a single vessel by its identifier.
    """

    try:
        params = event.get("pathParameters") or {}
        payload = GetVesselRequest(**params)
        data = service.get_vessel(payload)
        response = format_response(True, data, "Vessel fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def create_vessel_assignment_handler(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Assign a crew member or inspector to a vessel (admin only).
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        body = parse_json_body(event)
        payload = CreateVesselAssignmentRequest(**body)
        data = vessel_assignment_service.create_assignment(admin_id, payload)
        response = format_response(True, data, "Vessel assignment created successfully")
        return {"statusCode": 201, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def get_vessel_assignments_handler(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Get all assignments (crew and inspectors) for a vessel.
    """

    try:
        query_params = event.get("queryStringParameters") or {}
        vessel_id = query_params.get("vessel_id")
        if not vessel_id:
            raise ValueError("vessel_id query parameter is required")

        payload = GetVesselAssignmentsRequest(vessel_id=vessel_id)
        data = vessel_assignment_service.get_assignments(payload)
        response = format_response(True, data, "Vessel assignments fetched successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def delete_vessel_assignment_handler(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Delete a vessel assignment by assignment_id (admin only).
    """

    try:
        params = event.get("pathParameters") or {}
        assignment_id = params.get("assignment_id")
        if not assignment_id:
            raise ValueError("assignment_id path parameter is required")

        data = vessel_assignment_service.delete_assignment(assignment_id)
        response = format_response(True, data, "Vessel assignment deleted successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)

