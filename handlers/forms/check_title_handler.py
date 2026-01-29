"""
Lambda handler for checking if a form title already exists.
"""
from typing import Any, Dict

from models.response.api import ApiResponse
from repository.inspection_form_repository import InspectionFormRepository
from utility.auth import authenticate_admin
from utility.logger import get_logger
from utility.response import create_response


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Check if a form title already exists among active forms.
    
    Query Parameters:
        - title: Form title to check (required)
        - exclude_form_id: Form ID to exclude from check (optional, for updates)
    
    Returns:
        200: { exists: boolean, message?: string }
    """
    logger = get_logger(__name__)
    
    try:
        # Authenticate admin
        admin_id = authenticate_admin(event)
        
        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        title = query_params.get("title", "").strip()
        exclude_form_id = query_params.get("exclude_form_id")
        
        if not title:
            return create_response(
                400,
                ApiResponse(
                    success=False,
                    data=None,
                    message="Title parameter is required",
                    error="missing_title",
                ).dict(),
            )
        
        # Check if title exists
        repository = InspectionFormRepository()
        existing_form = repository.find_active_form_by_title(title, exclude_form_id=exclude_form_id)
        
        if existing_form:
            logger.info(
                "Form title '%s' already exists (form_id: %s) for admin %s",
                title,
                existing_form.get("form_id"),
                admin_id,
            )
            return create_response(
                200,
                ApiResponse(
                    success=True,
                    data={
                        "exists": True,
                        "message": f"A form with the title '{title}' already exists and is active. Please choose a different title.",
                    },
                    message="Title check completed",
                    error=None,
                ).dict(),
            )
        
        logger.info("Form title '%s' is available for admin %s", title, admin_id)
        return create_response(
            200,
            ApiResponse(
                success=True,
                data={
                    "exists": False,
                    "message": None,
                },
                message="Title check completed",
                error=None,
            ).dict(),
        )
    
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Failed to check form title: %s", exc)
        return create_response(
            500,
            ApiResponse(
                success=False,
                data=None,
                message="Failed to check form title",
                error=str(exc),
            ).dict(),
        )
