"""
Lambda handlers for dashboard operations (admin only).
"""
import json
from typing import Any, Dict

from config.jwt_config import get_subject_from_access_token
from services.dashboard_service import DashboardService
from utility.cors import cors_middleware
from utility.error_handler import handle_error
from utility.response import format_response


service = DashboardService()


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
def get_dashboard_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    Get dashboard data handler.
    """

    try:
        admin_id = _get_admin_id_from_event(event)
        data = service.get_dashboard_data(admin_id)
        response = format_response(True, data, "Dashboard data fetched successfully")
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return handle_error(exc)
