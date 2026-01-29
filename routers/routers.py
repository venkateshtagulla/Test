"""
Comprehensive FastAPI router configuration for ALL API endpoints.
This creates FastAPI routes that wrap the existing Lambda handlers.
"""
from fastapi import APIRouter, Header, Request, Query, File, UploadFile
from typing import Optional, List

# Import all Lambda handlers
from routers.lambda.auth import (
    register_handler as inspector_register,
    login_handler as inspector_login,
    profile_handler as inspector_profile,
    inspector_me_handler,
    inspector_dashboard_handler,
    inspector_sync_handler,
)
from routers.lambda.admin_auth import (
    admin_register_handler,
    admin_login_handler,
    admin_profile_handler,
    admin_me_handler,
)
from routers.lambda.admin_inspector import (
    admin_create_inspector_handler,
    admin_get_inspector_handler,
    admin_list_inspectors_handler,
    admin_reset_inspector_password_handler,
)
from routers.lambda.vessel import (
    create_vessel_handler,
    list_vessels_handler,
    get_vessel_handler,
    create_vessel_assignment_handler,
    get_vessel_assignments_handler,
)
from routers.lambda.crew import (
    create_crew_handler,
    get_crew_handler,
    list_crew_handler,
    register_crew_handler,
    login_crew_handler,
    admin_reset_crew_password_handler,
    crew_me_handler,
    crew_dashboard_handler,
    crew_sync_handler,
)
from routers.lambda.inspection_form import (
    create_inspection_form_handler,
    get_inspection_form_handler,
    update_inspection_form_handler,
    delete_inspection_form_handler,
    list_inspection_forms_handler,
    list_submitted_forms_handler,
    list_inspector_forms_handler,
    submit_inspection_form_handler,
)
from routers.lambda.inspection_assignment import (
    create_inspection_assignment_handler,
    bulk_create_inspection_assignment_handler,
    get_inspection_assignment_handler,
    list_inspection_assignments_handler,
    list_inspector_assignments_handler,
    create_crew_inspection_assignment_handler,
    list_crew_assignments_handler,
    delete_inspection_assignment_handler,
)
from routers.lambda.defect import (
    list_defects_handler,
    get_defect_handler,
    approve_defect_handler,
    close_defect_handler,
    add_comment_handler,
    update_defect_handler,
    create_inspector_defect_handler,
    list_inspector_defects_handler,
    create_crew_defect_handler,
    list_crew_defects_handler,
    add_inspector_defect_analysis_handler,
    add_crew_defect_analysis_handler,
)
from routers.lambda.upload import presign_upload_handler
from routers.lambda.dashboard import get_dashboard_handler

from utility.lambda_to_fastapi import lambda_to_fastapi_response

# Create main API router
api_router = APIRouter()

# ============================================================================
# INSPECTOR AUTHENTICATION ROUTES
# ============================================================================
inspector_router = APIRouter(prefix="/inspectors", tags=["Inspector Authentication"])

@inspector_router.post("/register", summary="Register Inspector")
async def register_inspector_route(request: Request):
    """Register a new inspector account."""
    event = await lambda_to_fastapi_response(request)
    return inspector_register(event, None)

@inspector_router.post("/login", summary="Login Inspector")
async def login_inspector_route(request: Request):
    """Login an existing inspector."""
    event = await lambda_to_fastapi_response(request)
    return inspector_login(event, None)

@inspector_router.get("/{inspector_id}", summary="Get Inspector Profile")
async def get_inspector_profile_route(inspector_id: str, request: Request):
    """Get inspector profile by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"inspector_id": inspector_id})
    return inspector_profile(event, None)

@inspector_router.get("/dashboard", summary="Get Inspector Dashboard")
async def get_inspector_dashboard_route(request: Request, authorization: Optional[str] = Header(None)):
    """Get dashboard data for the authenticated inspector."""   
    event = await lambda_to_fastapi_response(request)
    return inspector_dashboard_handler(event, None)

@inspector_router.post("/sync", summary="Check Inspector Sync Status")
async def check_inspector_sync_route(request: Request, authorization: Optional[str] = Header(None)):
    """Check sync status for the authenticated inspector."""
    event = await lambda_to_fastapi_response(request)
    return inspector_sync_handler(event, None)

# ============================================================================
# INSPECTOR ME ROUTE (separate to avoid path conflicts)
# ============================================================================
inspector_me_router = APIRouter(prefix="/inspector", tags=["Inspector Authentication"])

@inspector_me_router.get("/me", summary="Get Current Inspector Profile")
async def get_current_inspector_route(request: Request, authorization: Optional[str] = Header(None)):
    """Get the currently authenticated inspector's profile."""
    event = await lambda_to_fastapi_response(request)
    return inspector_me_handler(event, None)

# ============================================================================
# ADMIN AUTHENTICATION ROUTES
# ============================================================================
admin_router = APIRouter(prefix="/admins", tags=["Admin Authentication"])

@admin_router.post("/register", summary="Register Admin")
async def register_admin_route(request: Request):
    """Register a new admin account."""
    event = await lambda_to_fastapi_response(request)
    return admin_register_handler(event, None)

@admin_router.post("/login", summary="Login Admin")
async def login_admin_route(request: Request):
    """Login an existing admin."""
    event = await lambda_to_fastapi_response(request)
    return admin_login_handler(event, None)

@admin_router.get("/{admin_id}", summary="Get Admin Profile")
async def get_admin_profile_route(admin_id: str, request: Request):
    """Get admin profile by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"admin_id": admin_id})
    return admin_profile_handler(event, None)

# ============================================================================
# ADMIN PROFILE ROUTE (separate prefix)
# ============================================================================
admin_profile_router = APIRouter(prefix="/admin", tags=["Admin Authentication"])

@admin_profile_router.get("/profile", summary="Get Current Admin Profile")
async def get_current_admin_route(request: Request, authorization: Optional[str] = Header(None)):
    """Get the currently authenticated admin's profile."""
    event = await lambda_to_fastapi_response(request)
    return admin_me_handler(event, None)

# ============================================================================
# ADMIN INSPECTOR MANAGEMENT ROUTES
# ============================================================================
admin_inspector_router = APIRouter(prefix="/admin/inspectors", tags=["Admin - Inspector Management"])

@admin_inspector_router.post("", summary="Create Inspector (Admin)")
async def admin_create_inspector_route(request: Request, authorization: Optional[str] = Header(None)):
    """Admin creates a new inspector with documents and password."""
    event = await lambda_to_fastapi_response(request)
    return admin_create_inspector_handler(event, None)

@admin_inspector_router.get("", summary="List Inspectors (Admin)")
async def admin_list_inspectors_route(
    request: Request,
    page: int = Query(1),
    limit: int = Query(20),
    authorization: Optional[str] = Header(None)
):
    """Admin lists all inspectors with pagination."""
    event = await lambda_to_fastapi_response(request, query_params={"page": str(page), "limit": str(limit)})
    return admin_list_inspectors_handler(event, None)

@admin_inspector_router.get("/{inspector_id}", summary="Get Inspector (Admin)")
async def admin_get_inspector_route(inspector_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin gets inspector details by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"inspector_id": inspector_id})
    return admin_get_inspector_handler(event, None)

@admin_inspector_router.post("/{inspector_id}/reset-password", summary="Reset Inspector Password (Admin)")
async def admin_reset_inspector_password_route(inspector_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin resets an inspector's password."""
    event = await lambda_to_fastapi_response(request, path_params={"inspector_id": inspector_id})
    return admin_reset_inspector_password_handler(event, None)

# ============================================================================
# VESSEL MANAGEMENT ROUTES
# ============================================================================
vessel_router = APIRouter(prefix="/vessels", tags=["Vessel Management"])

@vessel_router.post("", summary="Create Vessel")
async def create_vessel_route(request: Request, authorization: Optional[str] = Header(None)):
    """Create a new vessel (admin only)."""
    event = await lambda_to_fastapi_response(request)
    return create_vessel_handler(event, None)

@vessel_router.get("", summary="List Vessels")
async def list_vessels_route(
    request: Request,
    page: int = Query(1),
    limit: int = Query(20),
    authorization: Optional[str] = Header(None)
):
    """List all vessels for the authenticated admin with pagination."""
    event = await lambda_to_fastapi_response(request, query_params={"page": str(page), "limit": str(limit)})
    return list_vessels_handler(event, None)

@vessel_router.get("/{vessel_id}", summary="Get Vessel")
async def get_vessel_route(vessel_id: str, request: Request):
    """Get a single vessel by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id})
    return get_vessel_handler(event, None)

@vessel_router.post("/assignments", summary="Create Vessel Assignment")
async def create_vessel_assignment_route(request: Request, authorization: Optional[str] = Header(None)):
    """Assign a crew member or inspector to a vessel (admin only)."""
    event = await lambda_to_fastapi_response(request)
    return create_vessel_assignment_handler(event, None)

@vessel_router.get("/assignments", summary="Get Vessel Assignments")
async def get_vessel_assignments_route(request: Request, vessel_id: str = Query(...)):
    """Get all assignments (crew and inspectors) for a vessel."""
    event = await lambda_to_fastapi_response(request, query_params={"vessel_id": vessel_id})
    return get_vessel_assignments_handler(event, None)

# ============================================================================
# CREW MANAGEMENT ROUTES
# ============================================================================
crew_router = APIRouter(prefix="/crew", tags=["Crew Management"])

@crew_router.post("", summary="Create Crew Member")
async def create_crew_route(request: Request, authorization: Optional[str] = Header(None)):
    """Create a new crew member (admin only)."""
    event = await lambda_to_fastapi_response(request)
    return create_crew_handler(event, None)

@crew_router.get("", summary="List Crew Members")
async def list_crew_route(
    request: Request,
    page: int = Query(1),
    limit: int = Query(20),
    authorization: Optional[str] = Header(None)
):
    """List all crew members with pagination (admin only)."""
    event = await lambda_to_fastapi_response(request, query_params={"page": str(page), "limit": str(limit)})
    return list_crew_handler(event, None)

@crew_router.get("/{crew_id}", summary="Get Crew Member")
async def get_crew_route(crew_id: str, request: Request):
    """Get crew member details by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"crew_id": crew_id})
    return get_crew_handler(event, None)

@crew_router.post("/register", summary="Register Crew Member")
async def register_crew_route(request: Request):
    """Register a new crew member account."""
    event = await lambda_to_fastapi_response(request)
    return register_crew_handler(event, None)

@crew_router.post("/login", summary="Login Crew Member")
async def login_crew_route(request: Request):
    """Login an existing crew member."""
    event = await lambda_to_fastapi_response(request)
    return login_crew_handler(event, None)

@crew_router.get("/me", summary="Get Current Crew Profile")
async def get_current_crew_route(request: Request, authorization: Optional[str] = Header(None)):
    """Get the currently authenticated crew member's profile."""
    event = await lambda_to_fastapi_response(request)
    return crew_me_handler(event, None)

@crew_router.get("/dashboard", summary="Get Crew Dashboard")
async def get_crew_dashboard_route(request: Request, authorization: Optional[str] = Header(None)):
    """Get dashboard data for the authenticated crew member."""
    event = await lambda_to_fastapi_response(request)
    return crew_dashboard_handler(event, None)

@crew_router.post("/sync", summary="Check Crew Sync Status")
async def check_crew_sync_route(request: Request, authorization: Optional[str] = Header(None)):
    """Check sync status for the authenticated crew member."""
    event = await lambda_to_fastapi_response(request)
    return crew_sync_handler(event, None)

@crew_router.get("/assignments", summary="List Crew Assignments")
async def list_crew_assignments_route(request: Request, authorization: Optional[str] = Header(None)):
    """List inspection assignments for the authenticated crew member."""
    event = await lambda_to_fastapi_response(request)
    return list_crew_assignments_handler(event, None)

@crew_router.post("/{crew_id}/inspection-assignments", summary="Create Crew Inspection Assignment")
async def create_crew_inspection_assignment_route(crew_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Create a single inspection assignment to a crew member."""
    event = await lambda_to_fastapi_response(request, path_params={"crew_id": crew_id})
    return create_crew_inspection_assignment_handler(event, None)

# ============================================================================
# ADMIN CREW ROUTES
# ============================================================================
admin_crew_router = APIRouter(prefix="/admin/crew", tags=["Admin - Crew Management"])

@admin_crew_router.post("/{crew_id}/reset-password", summary="Reset Crew Password (Admin)")
async def admin_reset_crew_password_route(crew_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin resets a crew member's password."""
    event = await lambda_to_fastapi_response(request, path_params={"crew_id": crew_id})
    return admin_reset_crew_password_handler(event, None)

# ============================================================================
# INSPECTION FORM ROUTES
# ============================================================================
form_router = APIRouter(prefix="/forms", tags=["Inspection Forms"])

@form_router.post("", summary="Create Inspection Form")
async def create_form_route(request: Request, authorization: Optional[str] = Header(None)):
    """Create a new inspection form with ordered questions."""
    event = await lambda_to_fastapi_response(request)
    return create_inspection_form_handler(event, None)

@form_router.get("", summary="List Inspection Forms")
async def list_forms_route(request: Request, authorization: Optional[str] = Header(None)):
    """List inspection forms with pagination."""
    event = await lambda_to_fastapi_response(request)
    return list_inspection_forms_handler(event, None)

@form_router.get("/{form_id}", summary="Get Inspection Form")
async def get_form_route(form_id: str, request: Request):
    """Get inspection form by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"form_id": form_id})
    return get_inspection_form_handler(event, None)

@form_router.put("/{form_id}", summary="Update Inspection Form")
async def update_form_route(form_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Update inspection form by ID (admin only)."""
    event = await lambda_to_fastapi_response(request, path_params={"form_id": form_id})
    return update_inspection_form_handler(event, None)

@form_router.delete("/{form_id}", summary="Delete Inspection Form")
async def delete_form_route(form_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Deactivate an inspection form by ID (admin only)."""
    event = await lambda_to_fastapi_response(request, path_params={"form_id": form_id})
    return delete_inspection_form_handler(event, None)

# ============================================================================
# INSPECTOR FORM ROUTES
# ============================================================================
inspector_form_router = APIRouter(prefix="/inspectors/forms", tags=["Inspector - Inspection Forms"])

@inspector_form_router.get("", summary="List Inspector Forms")
async def list_inspector_forms_route(request: Request, authorization: Optional[str] = Header(None)):
    """List inspection forms assigned to the authenticated inspector."""
    event = await lambda_to_fastapi_response(request)
    return list_inspector_forms_handler(event, None)

@inspector_form_router.post("/{form_id}/submit", summary="Submit Inspection Form")
async def submit_form_route(form_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Submit/fill an inspection form by the authenticated inspector."""
    event = await lambda_to_fastapi_response(request, path_params={"form_id": form_id})
    return submit_inspection_form_handler(event, None)

# ============================================================================
# ADMIN FORM ROUTES
# ============================================================================
admin_form_router = APIRouter(prefix="/admin/forms", tags=["Admin - Inspection Forms"])

@admin_form_router.get("/submitted", summary="List Submitted Forms (Admin)")
async def list_submitted_forms_route(request: Request, authorization: Optional[str] = Header(None)):
    """List submitted (Closed) forms with answers for admin view."""
    event = await lambda_to_fastapi_response(request)
    return list_submitted_forms_handler(event, None)

# ============================================================================
# INSPECTION ASSIGNMENT ROUTES
# ============================================================================
assignment_router = APIRouter(prefix="/inspection-assignments", tags=["Inspection Assignments"])

@assignment_router.post("", summary="Create Inspection Assignment")
async def create_assignment_route(request: Request, authorization: Optional[str] = Header(None)):
    """Create a new inspection assignment."""
    event = await lambda_to_fastapi_response(request)
    return create_inspection_assignment_handler(event, None)

@assignment_router.post("/bulk", summary="Bulk Create Inspection Assignments")
async def bulk_create_assignment_route(request: Request, authorization: Optional[str] = Header(None)):
    """Create multiple inspection assignments to an inspector."""
    event = await lambda_to_fastapi_response(request)
    return bulk_create_inspection_assignment_handler(event, None)

@assignment_router.get("", summary="List Inspection Assignments")
async def list_assignments_route(request: Request, authorization: Optional[str] = Header(None)):
    """List inspection assignments with pagination."""
    event = await lambda_to_fastapi_response(request)
    return list_inspection_assignments_handler(event, None)

@assignment_router.get("/{assignment_id}", summary="Get Inspection Assignment")
async def get_assignment_route(assignment_id: str, request: Request):
    """Get inspection assignment by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"assignment_id": assignment_id})
    return get_inspection_assignment_handler(event, None)

@assignment_router.delete("/form/{form_id}", summary="Delete Inspection Assignment")
async def delete_assignment_route(form_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Remove a form from its assignment by form_id."""
    event = await lambda_to_fastapi_response(request, path_params={"form_id": form_id})
    return delete_inspection_assignment_handler(event, None)

# ============================================================================
# INSPECTOR ASSIGNMENT ROUTES
# ============================================================================
inspector_assignment_router = APIRouter(prefix="/inspectors/assignments", tags=["Inspector - Assignments"])

@inspector_assignment_router.get("", summary="List Inspector Assignments")
async def list_inspector_assignments_route(request: Request, authorization: Optional[str] = Header(None)):
    """List inspection assignments for the authenticated inspector."""
    event = await lambda_to_fastapi_response(request)
    return list_inspector_assignments_handler(event, None)

# ============================================================================
# DEFECT MANAGEMENT ROUTES (ADMIN)
# ============================================================================
admin_defect_router = APIRouter(prefix="/admin/defects", tags=["Admin - Defect Management"])

@admin_defect_router.get("", summary="List Defects (Admin)")
async def list_defects_route(request: Request, authorization: Optional[str] = Header(None)):
    """List defects with pagination and optional filtering."""
    event = await lambda_to_fastapi_response(request)
    return list_defects_handler(event, None)

@admin_defect_router.get("/{defect_id}", summary="Get Defect (Admin)")
async def get_defect_route(defect_id: str, request: Request):
    """Get defect by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"defect_id": defect_id})
    return get_defect_handler(event, None)

@admin_defect_router.post("/{defect_id}/approve", summary="Approve Defect Resolution")
async def approve_defect_route(defect_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Approve defect resolution."""
    event = await lambda_to_fastapi_response(request, path_params={"defect_id": defect_id})
    return approve_defect_handler(event, None)

@admin_defect_router.post("/{defect_id}/close", summary="Close Defect")
async def close_defect_route(defect_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Close defect."""
    event = await lambda_to_fastapi_response(request, path_params={"defect_id": defect_id})
    return close_defect_handler(event, None)

@admin_defect_router.post("/{defect_id}/comments", summary="Add Defect Comment")
async def add_defect_comment_route(defect_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Add admin comment to defect."""
    event = await lambda_to_fastapi_response(request, path_params={"defect_id": defect_id})
    return add_comment_handler(event, None)

@admin_defect_router.put("/{defect_id}", summary="Update Defect")
async def update_defect_route(defect_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Update defect fields."""
    event = await lambda_to_fastapi_response(request, path_params={"defect_id": defect_id})
    return update_defect_handler(event, None)

# ============================================================================
# INSPECTOR DEFECT ROUTES
# ============================================================================
inspector_defect_router = APIRouter(prefix="/inspectors/defects", tags=["Inspector - Defects"])

@inspector_defect_router.post("", summary="Create Defect (Inspector)")
async def create_inspector_defect_route(request: Request, authorization: Optional[str] = Header(None)):
    """Inspector creates a new defect from the mobile/web app."""
    event = await lambda_to_fastapi_response(request)
    return create_inspector_defect_handler(event, None)

@inspector_defect_router.get("", summary="List Inspector Defects")
async def list_inspector_defects_route(request: Request, authorization: Optional[str] = Header(None)):
    """List defects raised by the authenticated inspector."""
    event = await lambda_to_fastapi_response(request)
    return list_inspector_defects_handler(event, None)

@inspector_defect_router.post("/{defect_id}/analysis", summary="Add Defect Analysis (Inspector)")
async def add_inspector_defect_analysis_route(defect_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Add or update defect analysis for a defect by the authenticated inspector."""
    event = await lambda_to_fastapi_response(request, path_params={"defect_id": defect_id})
    return add_inspector_defect_analysis_handler(event, None)

# ============================================================================
# CREW DEFECT ROUTES
# ============================================================================
crew_defect_router = APIRouter(prefix="/crew/defects", tags=["Crew - Defects"])

@crew_defect_router.post("", summary="Create Defect (Crew)")
async def create_crew_defect_route(request: Request, authorization: Optional[str] = Header(None)):
    """Crew creates a new defect from the mobile app."""
    event = await lambda_to_fastapi_response(request)
    return create_crew_defect_handler(event, None)

@crew_defect_router.get("", summary="List Crew Defects")
async def list_crew_defects_route(request: Request, authorization: Optional[str] = Header(None)):
    """List defects raised by the authenticated crew member."""
    event = await lambda_to_fastapi_response(request)
    return list_crew_defects_handler(event, None)

@crew_defect_router.post("/{defect_id}/analysis", summary="Add Defect Analysis (Crew)")
async def add_crew_defect_analysis_route(defect_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Add or update defect analysis for a defect by the authenticated crew member."""
    event = await lambda_to_fastapi_response(request, path_params={"defect_id": defect_id})
    return add_crew_defect_analysis_handler(event, None)

# ============================================================================
# UPLOAD ROUTES
# ============================================================================
upload_router = APIRouter(prefix="/uploads", tags=["File Upload"])

@upload_router.post("/presign", summary="Get Presigned Upload URL")
async def presign_upload_route(request: Request, authorization: Optional[str] = Header(None)):
    """Get a presigned URL for uploading files to S3."""
    event = await lambda_to_fastapi_response(request)
    return presign_upload_handler(event, None)

# ============================================================================
# DASHBOARD ROUTES
# ============================================================================
dashboard_router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])

@dashboard_router.get("", summary="Get Admin Dashboard")
async def get_dashboard_route(request: Request, authorization: Optional[str] = Header(None)):
    """Get dashboard data for the authenticated admin."""
    event = await lambda_to_fastapi_response(request)
    return get_dashboard_handler(event, None)

# ============================================================================
# INCLUDE ALL ROUTERS IN MAIN API ROUTER
# ============================================================================
api_router.include_router(inspector_router)
api_router.include_router(inspector_me_router)
api_router.include_router(admin_router)
api_router.include_router(admin_profile_router)
api_router.include_router(admin_inspector_router)
api_router.include_router(vessel_router)
api_router.include_router(crew_router)
api_router.include_router(admin_crew_router)
api_router.include_router(form_router)
api_router.include_router(inspector_form_router)
api_router.include_router(admin_form_router)
api_router.include_router(assignment_router)
api_router.include_router(inspector_assignment_router)
api_router.include_router(admin_defect_router)
api_router.include_router(inspector_defect_router)
api_router.include_router(crew_defect_router)
api_router.include_router(upload_router)
api_router.include_router(dashboard_router)
