"""
FastAPI router for vessel management endpoints.
"""
from fastapi import APIRouter, Header, Request, Query
from typing import Optional

from routers.vessel import (
    create_vessel_handler,
    list_vessels_handler,
    get_vessel_handler,
    create_vessel_assignment_handler,
    get_vessel_assignments_handler,
    delete_vessel_assignment_handler,
)
from utility.lambda_to_fastapi import lambda_to_fastapi_response

router = APIRouter()


@router.post("", summary="Create Vessel")
async def create_vessel(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Create a new vessel (admin only).
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Request Body:**
    - ship_id: Ship identifier
    - ship_name: Ship name
    - ship_type: Type of ship
    - flag: Ship flag/country
    - imo_number: IMO number (optional)
    """
    event = await lambda_to_fastapi_response(request)
    return create_vessel_handler(event, None)


@router.get("", summary="List Vessels")
async def list_vessels(
    request: Request,
    page: int = Query(1, description="Page number"),
    limit: int = Query(20, description="Items per page"),
    authorization: Optional[str] = Header(None)
):
    """
    List all vessels for the authenticated admin with pagination.
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Query Parameters:**
    - page: Page number (default: 1)
    - limit: Items per page (default: 20)
    """
    event = await lambda_to_fastapi_response(request, query_params={"page": str(page), "limit": str(limit)})
    return list_vessels_handler(event, None)


@router.get("/{vessel_id}", summary="Get Vessel")
async def get_vessel(vessel_id: str, request: Request):
    """
    Get a single vessel by ID.
    
    **Path Parameters:**
    - vessel_id: Unique vessel identifier
    """
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id})
    return get_vessel_handler(event, None)


@router.post("/assignments", summary="Create Vessel Assignment")
async def create_vessel_assignment(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Assign a crew member or inspector to a vessel (admin only).
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Request Body:**
    - vessel_id: Vessel identifier
    - assignee_id: Inspector or crew member ID
    - assignee_type: Type of assignee ("inspector" or "crew")
    """
    event = await lambda_to_fastapi_response(request)
    return create_vessel_assignment_handler(event, None)


@router.get("/assignments", summary="Get Vessel Assignments")
async def get_vessel_assignments(
    request: Request,
    vessel_id: str = Query(..., description="Vessel ID")
):
    """
    Get all assignments (crew and inspectors) for a vessel.
    
    **Query Parameters:**
    - vessel_id: Vessel identifier (required)
    """
    event = await lambda_to_fastapi_response(request, query_params={"vessel_id": vessel_id})
    return get_vessel_assignments_handler(event, None)


@router.delete("/assignments/{assignment_id}", summary="Delete Vessel Assignment")
async def delete_vessel_assignment(
    assignment_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Delete a vessel assignment by assignment_id (admin only).
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Path Parameters:**
    - assignment_id: Assignment identifier to delete
    """
    event = await lambda_to_fastapi_response(request, path_params={"assignment_id": assignment_id})
    return delete_vessel_assignment_handler(event, None)
