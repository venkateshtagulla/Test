"""
Lambda handlers for inspection assignments.
"""
import json
from typing import Any, Dict

from config.jwt_config import get_subject_from_access_token
from repository.inspection_assignment_repository import InspectionAssignmentRepository
from services.inspection_assignment_service import InspectionAssignmentService
from utility.body_parser import parse_json_body
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.response import format_response


repository = InspectionAssignmentRepository()
service = InspectionAssignmentService(repository=repository)


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
def create_inspection_assignment_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Create inspection assignment handler.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        body = parse_json_body(event)
        data = service.create_assignment(admin_id, body)
        response = format_response(True, data, "Inspection assignment created successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def get_inspection_assignment_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Get inspection assignment by ID handler.
    """

    try:
        params = event.get("pathParameters") or {}
        data = service.get_assignment(params)
        response = format_response(True, data, "Inspection assignment fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_inspection_assignments_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List inspection assignments with pagination.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        query_params = event.get("queryStringParameters") or {}
        payload = {
            "form_id": query_params.get("form_id"),
            "page": int(query_params.get("page", 1)),
            "limit": int(query_params.get("limit", 20)),
            "search": query_params.get("search"),
        }
        data = service.list_assignments(admin_id, payload)
        response = format_response(True, data, "Inspection assignments fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_inspector_assignments_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List inspection assignments for the authenticated inspector.
    """

    try:
        inspector_id = _get_admin_id_from_event(event)  # Reuse token parser; subject is inspector_id for inspector tokens.
        query_params = event.get("queryStringParameters") or {}
        payload = {
            "form_id": query_params.get("form_id"),
            "page": int(query_params.get("page", 1)),
            "limit": int(query_params.get("limit", 20)),
            "search": query_params.get("search"),
        }
        data = service.list_assignments_for_inspector(inspector_id, payload)
        response = format_response(True, data, "Inspection assignments fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def bulk_create_inspection_assignment_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Create multiple inspection assignments to an inspector.
    Allows assigning multiple forms at once.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        body = parse_json_body(event)
        data = service.bulk_create_assignments(admin_id, body)
        response = format_response(True, data, f"Successfully created {data.get('count', 0)} inspection assignments")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def create_crew_inspection_assignment_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Create a single inspection assignment to a crew member.
    Validates that crew has no pending assignments before creating a new one.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        path_params = event.get("pathParameters") or {}
        crew_id = path_params.get("crew_id")
        if not crew_id:
            raise ValueError("Crew ID is required in path")

        body = parse_json_body(event)
        # Merge crew_id from path into body
        body["crew_id"] = crew_id
        data = service.create_crew_assignment(admin_id, body)
        response = format_response(True, data, "Crew inspection assignment created successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_crew_assignments_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List inspection assignments for the authenticated crew member.
    """

    try:
        crew_id = _get_admin_id_from_event(event)  # Reuse token parser; subject is crew_id for crew tokens.
        query_params = event.get("queryStringParameters") or {}
        payload = {
            "form_id": query_params.get("form_id"),
            "page": int(query_params.get("page", 1)),
            "limit": int(query_params.get("limit", 20)),
        }
        data = service.list_assignments_for_crew(crew_id, payload)
        response = format_response(True, data, "Inspection assignments fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def delete_inspection_assignment_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Remove a form from its assignment by form_id.
    Deletes the assignment record and updates form status to "Unassigned" if needed.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        path_params = event.get("pathParameters") or {}
        form_id = path_params.get("form_id")
        if not form_id:
            raise ValueError("Form ID is required in path")

        payload = {"form_id": form_id}
        data = service.remove_form_from_assignment(admin_id, payload)
        response = format_response(True, data, "Form successfully removed from assignment")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)
