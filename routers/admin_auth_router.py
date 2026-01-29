"""
FastAPI router for admin authentication endpoints.
"""
from fastapi import APIRouter, Header, Request
from typing import Optional

from routers.admin_auth import (
    admin_register_handler,
    admin_login_handler,
    admin_profile_handler,
    admin_me_handler,
)
from utility.lambda_to_fastapi import lambda_to_fastapi_response

router = APIRouter()


@router.post("/register", summary="Register Admin")
async def register_admin(request: Request):
    """
    Register a new admin account.
    
    **Request Body:**
    - email: Admin email address
    - password: Admin password
    - name: Admin full name
    """
    event = await lambda_to_fastapi_response(request)
    return admin_register_handler(event, None)


@router.post("/login", summary="Login Admin")
async def login_admin(request: Request):
    """
    Login an existing admin.
    
    **Request Body:**
    - email: Admin email address
    - password: Admin password
    
    **Returns:**
    - access_token: JWT access token
    - refresh_token: JWT refresh token
    - admin: Admin profile data
    """
    event = await lambda_to_fastapi_response(request)
    return admin_login_handler(event, None)


@router.get("/profile", summary="Get Current Admin Profile")
async def get_current_admin(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Get the currently authenticated admin's profile.
    
    **Headers:**
    - Authorization: Bearer {access_token}
    """
    event = await lambda_to_fastapi_response(request)
    return admin_me_handler(event, None)


@router.get("/{admin_id}", summary="Get Admin Profile")
async def get_admin_profile(admin_id: str, request: Request):
    """
    Get admin profile by ID.
    
    **Path Parameters:**
    - admin_id: Unique admin identifier
    """
    event = await lambda_to_fastapi_response(request, path_params={"admin_id": admin_id})
    return admin_profile_handler(event, None)


