"""
Lambda handler for creating and managing inspection forms.
"""
import json
import mimetypes
import re
from typing import Any, Dict, List, Optional

from config.jwt_config import get_subject_from_access_token
from repository.inspection_form_repository import InspectionFormRepository
from services.inspection_form_service import InspectionFormService
from utility.body_parser import parse_json_body
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.errors import ApiError
from utility.multipart_parser import parse_multipart_form_data
from utility.response import format_response
from utility.s3_utils import upload_file_to_s3, sign_s3_url_if_possible
from utility.json_encoder import json_dumps_safe


repository = InspectionFormRepository()
service = InspectionFormService(repository=repository)


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


def _extract_order_from_field_name(field_name: str) -> Optional[int]:
    """
    Extract question order from supported field name patterns.
    Supported base patterns:
    - question_<order>_image
    - q<order>_image
    - q<order>

    Also supports an optional numeric suffix that may be appended by the
    multipart parser for duplicate field names, e.g. question_1_image_2.
    """

    clean_name = field_name.strip()
    # Strip optional numeric suffix like _2, _3 that we may add for duplicate
    # field names in the multipart parser.
    match = re.match(r"^(.*?)(_\\d+)$", clean_name)
    if match:
        clean_name = match.group(1)

    if clean_name.startswith("question_") and clean_name.endswith("_image"):
        candidate = clean_name[len("question_") : -len("_image")]
    elif clean_name.startswith("q") and clean_name.endswith("_image"):
        candidate = clean_name[1:-len("_image")]
    else:
        return None

    try:
        return int(candidate)
    except (TypeError, ValueError):
        return None


def _normalize_questions(
    raw_questions: Any,
    media_by_order: Dict[int, str],
    allow_missing: bool,
) -> Optional[List[Dict[str, Any]]]:
    """
    Normalize questions payload (JSON string or list of dicts) and attach media URLs.
    """

    if raw_questions in (None, "", []):
        if allow_missing:
            return None
        raise ApiError("Questions are required", 400, "missing_questions")

    if isinstance(raw_questions, str):
        try:
            raw_questions = json.loads(raw_questions)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise ApiError("Invalid questions payload", 400, "invalid_questions_json") from exc

    if not isinstance(raw_questions, list):
        raise ApiError("Questions payload must be a list", 400, "invalid_questions_format")

    normalized: List[Dict[str, Any]] = []
    for item in raw_questions:
        if not isinstance(item, dict):
            raise ApiError("Each question must be an object", 400, "invalid_question_item")
        if "order" not in item:
            raise ApiError("Question order is required", 400, "missing_question_order")
        try:
            order = int(item.get("order"))
        except (TypeError, ValueError) as exc:
            raise ApiError("Question order must be a number", 400, "invalid_question_order") from exc

        media_url = media_by_order.get(order) or item.get("media_url") or item.get("image_url")
        
        # Build item dict based on type
        normalized_item = {
            "order": order,
            "type": item.get("type"),
        }
        
        # Add type-specific fields
        if item.get("type") == "section":
            normalized_item["title"] = item.get("title")
        else:
            normalized_item["prompt"] = item.get("prompt")
            normalized_item["options"] = item.get("options")
            normalized_item["media_url"] = media_url
            normalized_item["allow_image_upload"] = item.get("allow_image_upload")
        
        normalized.append(normalized_item)

    return normalized


def _extract_question_media(files: Dict[str, tuple]) -> Dict[int, str]:
    """
    Upload any question media files and return a mapping of order -> media URL.
    """

    media_by_order: Dict[int, str] = {}
    for field_name, (file_bytes, file_name) in files.items():
        order = _extract_order_from_field_name(field_name)
        if order is None:
            continue

        content_type, _ = mimetypes.guess_type(file_name)
        raw_url = upload_file_to_s3(
            file_content=file_bytes,
            file_name=file_name,
            folder="inspection-question-media",
            content_type=content_type or "application/octet-stream",
        )
        media_by_order[order] = sign_s3_url_if_possible(raw_url)
    return media_by_order


def _build_form_payload(event: Dict[str, Any], allow_missing_questions: bool) -> Dict[str, Any]:
    """
    Build payload for creating or updating forms, supporting JSON and multipart/form-data.
    """

    headers = event.get("headers") or {}
    content_type = (
        headers.get("Content-Type")
        or headers.get("content-type")
        or headers.get("Content-type")
        or ""
    )

    if "multipart/form-data" in content_type.lower():
        form_fields, files = parse_multipart_form_data(event)
        media_by_order = _extract_question_media(files)
        questions = _normalize_questions(
            form_fields.get("questions"),
            media_by_order=media_by_order,
            allow_missing=allow_missing_questions,
        )

        # Safely parse optional integer fields
        def _parse_int(value: Optional[str]) -> Optional[int]:
            if value is None or value == "":
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        payload: Dict[str, Any] = {
            "vessel_id": form_fields.get("vessel_id"),
            "title": form_fields.get("title"),
            "description": form_fields.get("description"),
            "due_date": form_fields.get("due_date"),
            "recurrence_start_date": form_fields.get("recurrence_start_date"),
            "recurrence_interval_value": _parse_int(form_fields.get("recurrence_interval_value")),
            "recurrence_interval_unit": form_fields.get("recurrence_interval_unit"),
            "reminder_before_value": _parse_int(form_fields.get("reminder_before_value")),
            "reminder_before_unit": form_fields.get("reminder_before_unit"),
            "status": form_fields.get("status"),
            "questions": questions,
        }

        if allow_missing_questions and questions is None:
            payload.pop("questions")

        return payload

    return parse_json_body(event)


@cors_middleware()
def create_inspection_form_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Create inspection form with ordered questions.
    """

    try:
        # Basic trace logging for debugging failed requests
        # NOTE: does not log secrets; only event keys.
        debug_payload = {
            "has_body": bool(event.get("body")),
            "content_length": len(event.get("body") or ""),
            "headers_keys": list((event.get("headers") or {}).keys()),
        }
        print(f"[DEBUG] incoming event meta: {debug_payload}")
        admin_id = _get_admin_id_from_event(event)
        body = _build_form_payload(event, allow_missing_questions=False)
        data = service.create_form(admin_id, body)
        response = format_response(True, data, "Inspection form created successfully")
        return {"statusCode": 201, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def get_inspection_form_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Get inspection form by ID API Gateway handler.
    Supports optional inspection_id query parameter to fetch responses associated with an inspection.
    """

    try:
        params = event.get("pathParameters") or {}
        query_params = event.get("queryStringParameters") or {}
        inspection_id = query_params.get("inspection_id")
        
        data = service.get_form_by_id(params, inspection_id=inspection_id)
        response = format_response(True, data, "Inspection form fetched successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def update_inspection_form_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Update inspection form by ID (admin only).
    Supports multipart/form-data for question media uploads.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        params = event.get("pathParameters") or {}
        form_id = params.get("form_id")
        if not form_id:
            raise ApiError("Form id is required in path", 400, "missing_form_id")

        body = _build_form_payload(event, allow_missing_questions=True)
        payload = {**body, "form_id": form_id}
        data = service.update_form(admin_id, payload)
        response = format_response(True, data, "Inspection form updated successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def delete_inspection_form_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Deactivate an inspection form by ID (admin only).
    Deactivated forms cannot accept submissions and won't appear in assignments.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        params = event.get("pathParameters") or {}
        form_id = params.get("form_id")
        if not form_id:
            raise ApiError("Form id is required in path", 400, "missing_form_id")

        data = service.deactivate_form(admin_id, form_id)
        response = format_response(True, data, "Inspection form deactivated successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_inspection_forms_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List inspection forms with pagination API Gateway handler.
    If vessel_id query parameter is provided, lists forms for that vessel.
    Otherwise, lists all forms created by the authenticated admin.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        query_params = event.get("queryStringParameters") or {}
        payload = {
            "vessel_id": query_params.get("vessel_id"),
            "page": int(query_params.get("page", 1)),
            "limit": int(query_params.get("limit", 20)),
            "search": query_params.get("search"),
        }
        data = service.list_forms(admin_id, payload)
        response = format_response(True, data, "Inspection forms fetched successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_submitted_forms_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List submitted (Closed) forms with answers for admin view.
    Supports filtering by inspector_id, crew_id, or vessel_id via query parameters.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        query_params = event.get("queryStringParameters") or {}
        payload = {
            "inspector_id": query_params.get("inspector_id"),
            "crew_id": query_params.get("crew_id"),
            "vessel_id": query_params.get("vessel_id"),
            "page": int(query_params.get("page", 1)),
            "limit": int(query_params.get("limit", 20)),
        }
        data = service.list_submitted_forms(admin_id, payload)
        response = format_response(True, data, "Submitted forms fetched successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def list_inspector_forms_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    List inspection forms assigned to the authenticated inspector.
    """

    try:
        inspector_id = get_subject_from_access_token(
            (event.get("headers") or {}).get("Authorization", "").removeprefix("Bearer ").strip()
            or (event.get("headers") or {}).get("authorization", "").removeprefix("Bearer ").strip()
        )
        query_params = event.get("queryStringParameters") or {}
        payload = {
            "vessel_id": None,
            "page": int(query_params.get("page", 1)),
            "limit": int(query_params.get("limit", 20)),
            "search": query_params.get("search"),
        }
        data = service.list_forms_for_inspector(inspector_id, payload)
        response = format_response(True, data, "Inspection forms fetched successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)


@cors_middleware()
def submit_inspection_form_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Submit/fill an inspection form by the authenticated inspector.
    """

    try:
        headers = event.get("headers") or {}
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = auth_header.removeprefix("Bearer ").strip()
        actor_id = get_subject_from_access_token(token)

        path_params = event.get("pathParameters") or {}
        form_id = path_params.get("form_id")
        if not form_id:
            raise ApiError("Form id is required in path", 400, "missing_form_id")

        # Detect content type for JSON vs multipart/form-data
        content_type = (
            headers.get("Content-Type")
            or headers.get("content-type")
            or headers.get("Content-type")
            or ""
        )

        if "multipart/form-data" in content_type.lower():
            # Expect fields in cleaner format:
            # - assignment_id (optional): string
            # - q1, q2, q3, ...: text/mcq answers (form field values)
            # - q1_image, q2_image, ...: image file uploads (uploaded to S3, answer becomes S3 URL)
            print("🚀 PROCESSING MULTIPART FORM - NEW LOGIC (TEXT + IMAGE SUPPORT)")
            form_fields, files = parse_multipart_form_data(event)

            # Normalize answers into a map keyed by order
            answers_by_order: Dict[int, str] = {}
            media_urls_by_order: Dict[int, str] = {}

            # Track which questions are marked as defects
            defects_by_order: Dict[int, bool] = {}
            
            # Process text/mcq answers from form fields (q1, q2, q3, etc.)
            for field_name, field_value in form_fields.items():
                if field_name == "assignment_id":
                    continue  # Skip assignment_id, handled separately
                
                # Check if field is q<number>_defect or q<number>_is_defect (defect marker)
                if field_name.endswith("_defect") or field_name.endswith("_is_defect"):
                    try:
                        # Extract order from q<number>_defect or q<number>_is_defect
                        order_str = field_name[1:].replace("_defect", "").replace("_is_defect", "")
                        order = int(order_str)
                        # Mark as defect if value is truthy (true, 1, "true", etc.)
                        defect_value = str(field_value).strip().lower()
                        defects_by_order[order] = defect_value in ("true", "1", "yes", "on")
                    except (ValueError, TypeError):
                        continue  # Skip invalid defect fields
                    continue  # Skip processing as answer
                
                # Check if field is q<number> format
                if field_name.startswith("q") and field_name[1:].isdigit():
                    try:
                        order = int(field_name[1:])
                        value = str(field_value).strip()
                        if value:
                            answers_by_order[order] = value
                            # Also check if answer value itself is "Defect" (case-insensitive)
                            if value.lower() == "defect":
                                defects_by_order[order] = True
                    except (ValueError, TypeError):
                        continue  # Skip invalid q fields

            # Handle image file uploads (q1_image, q2_image, etc.)
            for field_name, (file_bytes, file_name) in files.items():
                if not field_name.startswith("q") or not field_name.endswith("_image"):
                    continue
                
                try:
                    # Extract order from q<order>_image
                    order_str = field_name[1:-6]  # Remove 'q' prefix and '_image' suffix
                    order = int(order_str)
                except (ValueError, TypeError):
                    continue  # Skip invalid image field names

                # Upload to S3 and store URL separately
                raw_url = upload_file_to_s3(
                    file_content=file_bytes,
                    file_name=file_name,
                    folder="inspection-answers",
                    content_type=None,
                )
                s3_url = sign_s3_url_if_possible(raw_url)
                media_urls_by_order[order] = s3_url

            if not answers_by_order and not media_urls_by_order:
                raise ApiError("At least one answer or image is required", 400, "missing_answers")

            # Convert to required format for service layer
            # Get all unique orders from both textual answers and media uploads
            all_orders = set(answers_by_order.keys()) | set(media_urls_by_order.keys())
            
            merged_answers = []
            for order in sorted(all_orders):
                merged_answers.append({
                    "order": order,
                    "value": answers_by_order.get(order),      # Text answer (can be None)
                    "media_url": media_urls_by_order.get(order) # Image URL (can be None)
                })

            # Extract inspection_id (aliased as assignment_id in some forms, or explicit inspection_id)
            # Preference: inspection_id > assignment_id
            inspection_id = form_fields.get("inspection_id") or form_fields.get("assignment_id")

            body = {
                "assignment_id": form_fields.get("assignment_id"),
                "answers": merged_answers,
                "defects": [order for order, is_defect in defects_by_order.items() if is_defect],
            }
        else:
            # Fallback to standard JSON body
            body = parse_json_body(event)
            inspection_id = body.get("inspection_id") or body.get("assignment_id")

        payload = {**body, "form_id": form_id}
        data = service.submit_form(actor_id, payload, inspection_id=inspection_id)
        response = format_response(True, data, "Inspection form submitted successfully")
        return {"statusCode": 200, "body": json_dumps_safe(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)
