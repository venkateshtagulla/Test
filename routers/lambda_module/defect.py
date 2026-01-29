"""
Lambda handlers for defect management operations (admin only).
"""
import json
import mimetypes
from typing import Any, Dict, List

from config.jwt_config import get_subject_from_access_token
from repository.defect_repository import DefectRepository
from services.defect_service import DefectService
from utility.body_parser import parse_json_body
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.multipart_parser import parse_multipart_form_data
from utility.response import format_response
from utility.s3_utils import upload_file_to_s3, sign_s3_url_if_possible


repository = DefectRepository()
service = DefectService(repository=repository)


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


def _get_actor_id_from_event(event: Dict[str, Any]) -> str:
    """
    Extract generic actor id (admin / inspector / crew) from Authorization header.
    """

    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()
    return get_subject_from_access_token(token)


def _build_create_defect_payload_from_multipart(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse multipart/form-data for defect creation and build a payload dict
    compatible with dictionary input expected by service.
    """

    form_fields, files = parse_multipart_form_data(event)

    # Upload any attached photos. We accept any file field and treat all as photos.
    photo_urls: List[str] = []
    for _, (file_bytes, file_name) in files.items():
        content_type, _ = mimetypes.guess_type(file_name)
        raw_url = upload_file_to_s3(
            file_content=file_bytes,
            file_name=file_name,
            folder="defect-attachments",
            content_type=content_type or "application/octet-stream",
        )
        photo_urls.append(sign_s3_url_if_possible(raw_url))

    payload: Dict[str, Any] = {
        "vessel_id": form_fields.get("vessel_id"),
        "form_id": form_fields.get("form_id"),
        "assignment_id": form_fields.get("assignment_id"),
        "title": form_fields.get("title"),
        "description": form_fields.get("description"),
        "severity": form_fields.get("severity", "minor"),
        "priority": form_fields.get("priority", "medium"),
        "location_on_ship": form_fields.get("location_on_ship"),
        "equipment_name": form_fields.get("equipment_name"),
        "assignee_id": form_fields.get("assignee_id"),
        "assignee_type": form_fields.get("assignee_type"),
        "due_date": form_fields.get("due_date"),
        "photos": photo_urls or None,
    }

    return payload


def _build_analysis_payload_from_multipart(event: Dict[str, Any], defect_id: str) -> Dict[str, Any]:
    """
    Parse multipart/form-data for defect analysis submission and build payload
    compatible with dictionary input expected by service.
    """

    form_fields, files = parse_multipart_form_data(event)

    photo_urls: List[str] = []
    for _, (file_bytes, file_name) in files.items():
        content_type, _ = mimetypes.guess_type(file_name)
        raw_url = upload_file_to_s3(
            file_content=file_bytes,
            file_name=file_name,
            folder="defect-analysis",
            content_type=content_type or "application/octet-stream",
        )
        photo_urls.append(sign_s3_url_if_possible(raw_url))

    payload: Dict[str, Any] = {
        "defect_id": defect_id,
        "root_cause": form_fields.get("root_cause"),
        "impact_assessment": form_fields.get("impact_assessment"),
        "recurrence_probability": form_fields.get("recurrence_probability"),
        "notes": form_fields.get("notes"),
        "photos": photo_urls or None,
    }

    return payload


@cors_middleware()
def list_defects_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List defects with pagination and optional filtering.
    """

    try:
        _get_admin_id_from_event(event)  # Verify admin authentication
        query_params = event.get("queryStringParameters") or {}
        payload = {
            "status": query_params.get("status"),
            "vessel_id": query_params.get("vessel_id"),
            "page": int(query_params.get("page", 1)),
            "limit": int(query_params.get("limit", 20)),
        }
        data = service.list_defects(payload)
        response = format_response(True, data, "Defects fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def get_defect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Get defect by ID handler.
    """

    try:
        _get_admin_id_from_event(event)  # Verify admin authentication
        params = event.get("pathParameters") or {}
        data = service.get_defect(params)
        response = format_response(True, data, "Defect fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def approve_defect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Approve defect resolution handler.
    Comment in body is optional.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        params = event.get("pathParameters") or {}
        # Body is optional for this endpoint (comment is optional)
        raw_body = event.get("body")
        if raw_body and raw_body.strip():
            body = parse_json_body(event)
        else:
            body = {}
        # Merge defect_id from path into body
        body["defect_id"] = params.get("defect_id")
        data = service.approve_defect(admin_id, body)
        response = format_response(True, data, "Defect approved successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def close_defect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Close defect handler.
    Comment in body is optional.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        params = event.get("pathParameters") or {}
        # Body is optional for this endpoint (comment is optional)
        raw_body = event.get("body")
        if raw_body and raw_body.strip():
            body = parse_json_body(event)
        else:
            body = {}
        # Merge defect_id from path into body
        body["defect_id"] = params.get("defect_id")
        data = service.close_defect(admin_id, body)
        response = format_response(True, data, "Defect closed successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def add_comment_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Add admin comment to defect handler.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        params = event.get("pathParameters") or {}
        body = parse_json_body(event)
        # Merge defect_id from path into body
        body["defect_id"] = params.get("defect_id")
        data = service.add_comment(admin_id, body)
        response = format_response(True, data, "Comment added successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def update_defect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Update defect fields handler.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        params = event.get("pathParameters") or {}
        body = parse_json_body(event)
        # Merge defect_id from path into body
        body["defect_id"] = params.get("defect_id")
        data = service.update_defect(admin_id, body)
        response = format_response(True, data, "Defect updated successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def create_inspector_defect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Inspector-facing endpoint to create a new defect from the mobile/web app.
    Supports multipart/form-data for a single photo or multiple attachments.
    """

    try:
        inspector_id = _get_actor_id_from_event(event)
        headers = event.get("headers") or {}
        content_type = (
            headers.get("Content-Type")
            or headers.get("content-type")
            or headers.get("Content-type")
            or ""
        )

        if "multipart/form-data" in content_type.lower():
            body = _build_create_defect_payload_from_multipart(event)
        else:
            body = parse_json_body(event)

        data = service.create_defect_for_inspector(inspector_id, body)
        response = format_response(True, data, "Defect created successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_inspector_defects_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List defects raised by the authenticated inspector with pagination.
    """

    try:
        inspector_id = _get_actor_id_from_event(event)
        query_params = event.get("queryStringParameters") or {}
        payload = {
            "status": query_params.get("status"),
            "vessel_id": query_params.get("vessel_id"),
            "page": int(query_params.get("page", 1)),
            "limit": int(query_params.get("limit", 20)),
        }
        data = service.list_defects_for_inspector(inspector_id, payload)
        response = format_response(True, data, "Defects fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def create_crew_defect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Crew-facing endpoint to create a new defect from the mobile app.
    """

    try:
        crew_id = _get_actor_id_from_event(event)
        headers = event.get("headers") or {}
        content_type = (
            headers.get("Content-Type")
            or headers.get("content-type")
            or headers.get("Content-type")
            or ""
        )

        if "multipart/form-data" in content_type.lower():
            body = _build_create_defect_payload_from_multipart(event)
        else:
            body = parse_json_body(event)

        data = service.create_defect_for_crew(crew_id, body)
        response = format_response(True, data, "Defect created successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_crew_defects_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List defects raised by the authenticated crew member with pagination.
    """

    try:
        crew_id = _get_actor_id_from_event(event)
        query_params = event.get("queryStringParameters") or {}
        payload = {
            "status": query_params.get("status"),
            "vessel_id": query_params.get("vessel_id"),
            "page": int(query_params.get("page", 1)),
            "limit": int(query_params.get("limit", 20)),
        }
        data = service.list_defects_for_crew(crew_id, payload)
        response = format_response(True, data, "Defects fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def add_inspector_defect_analysis_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Add or update defect analysis for a defect by the authenticated inspector.
    Supports JSON and multipart/form-data for photo upload.
    """

    try:
        inspector_id = _get_actor_id_from_event(event)
        params = event.get("pathParameters") or {}
        defect_id = params.get("defect_id")
        if not defect_id:
            raise ValueError("Defect ID is required in path")

        headers = event.get("headers") or {}
        content_type = (
            headers.get("Content-Type")
            or headers.get("content-type")
            or headers.get("Content-type")
            or ""
        )

        if "multipart/form-data" in content_type.lower():
            body = _build_analysis_payload_from_multipart(event, defect_id)
        else:
            body = parse_json_body(event)
            body["defect_id"] = defect_id

        data = service.add_defect_analysis_for_inspector(inspector_id, body)
        response = format_response(True, data, "Defect analysis submitted successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def add_crew_defect_analysis_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Add or update defect analysis for a defect by the authenticated crew member.
    Supports JSON and multipart/form-data for photo upload.
    """

    try:
        crew_id = _get_actor_id_from_event(event)
        params = event.get("pathParameters") or {}
        defect_id = params.get("defect_id")
        if not defect_id:
            raise ValueError("Defect ID is required in path")

        headers = event.get("headers") or {}
        content_type = (
            headers.get("Content-Type")
            or headers.get("content-type")
            or headers.get("Content-type")
            or ""
        )

        if "multipart/form-data" in content_type.lower():
            body = _build_analysis_payload_from_multipart(event, defect_id)
        else:
            body = parse_json_body(event)
            body["defect_id"] = defect_id

        data = service.add_defect_analysis_for_crew(crew_id, body)
        response = format_response(True, data, "Defect analysis submitted successfully")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)
