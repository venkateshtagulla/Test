"""
FastAPI router for inspector authentication endpoints.
Wraps Lambda handlers for local development with Swagger documentation.
"""
from fastapi import APIRouter, Header, Request
from typing import Optional

from routers.auth import (
    register_handler,
    login_handler,
    profile_handler,
    inspector_me_handler,
    inspector_dashboard_handler,
    inspector_sync_handler,
)
from utility.lambda_to_fastapi import lambda_to_fastapi_response

router = APIRouter()


@router.post("/register", summary="Register Inspector")
async def register_inspector(request: Request):
    """
    Register a new inspector account.
    
    **Request Body:**
    - email: Inspector email address
    - password: Inspector password
    - name: Inspector full name
    - phone: Inspector phone number (optional)
    """
    event = await lambda_to_fastapi_response(request)
    return register_handler(event, None)


@router.post("/login", summary="Login Inspector")
async def login_inspector(request: Request):
    """
    Login an existing inspector.
    
    **Request Body:**
    - email: Inspector email address
    - password: Inspector password
    
    **Returns:**
    - access_token: JWT access token
    - refresh_token: JWT refresh token
    - inspector: Inspector profile data
    """
    event = await lambda_to_fastapi_response(request)
    return login_handler(event, None)


@router.get("/{inspector_id}", summary="Get Inspector Profile")
async def get_inspector_profile(inspector_id: str, request: Request):
    """
    Get inspector profile by ID.
    
    **Path Parameters:**
    - inspector_id: Unique inspector identifier
    """
    event = await lambda_to_fastapi_response(request, path_params={"inspector_id": inspector_id})
    return profile_handler(event, None)


@router.get("/me", summary="Get Current Inspector Profile")
async def get_current_inspector(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Get the currently authenticated inspector's profile.
    
    **Headers:**
    - Authorization: Bearer {access_token}
    """
    event = await lambda_to_fastapi_response(request)
    return inspector_me_handler(event, None)


@router.get("/dashboard", summary="Get Inspector Dashboard")
async def get_inspector_dashboard(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Get dashboard data for the authenticated inspector.
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Returns:**
    - total_assignments: Total inspection assignments
    - pending_assignments: Pending assignments count
    - completed_assignments: Completed assignments count
    - recent_assignments: List of recent assignments
    """
    event = await lambda_to_fastapi_response(request)
    return inspector_dashboard_handler(event, None)


@router.post("/sync", summary="Check Inspector Sync Status")
async def check_inspector_sync(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Check sync status for the authenticated inspector.
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Returns:**
    - sync_status: Current synchronization status
    - last_sync: Last sync timestamp
    """
    event = await lambda_to_fastapi_response(request)
    return inspector_sync_handler(event, None)
