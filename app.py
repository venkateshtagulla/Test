"""
Comprehensive FastAPI router configuration for ALL API endpoints.
This creates FastAPI routes that wrap the existing Lambda handlers.
"""
from fastapi import APIRouter, Header, Request, Response, Query, File, UploadFile
from typing import Optional, List
# Import all Lambda handlers from routers/lambda/
from routers.lambda_module.auth import (
    register_handler as inspector_register,
    login_handler as inspector_login,
    profile_handler as inspector_profile,
    change_password_handler as inspector_change_password,
    inspector_me_handler,
    inspector_dashboard_handler,
    inspector_sync_handler,
)
from routers.lambda_module.admin_admin import(
    admin_create_admin_handler,
    admin_list_admins_handler,
    admin_get_admin_handler,
    admin_reset_admin_password_handler,
    admin_update_admin_handler,
    admin_delete_admin_handler)
from routers.lambda_module.admin_auth import (
    admin_register_handler,
    admin_login_handler,
    admin_profile_handler,
    admin_me_handler,
    admin_change_password_handler,
)
from routers.lambda_module.admin_inspector import (
    admin_create_inspector_handler,
    admin_get_inspector_handler,
    admin_list_inspectors_handler,
    admin_reset_inspector_password_handler,
    admin_delete_inspector_handler,
)
from routers.lambda_module.vessel import (
    create_vessel_handler,
    list_vessels_handler,
    get_vessel_handler,
    create_vessel_assignment_handler,
    get_vessel_assignments_handler,
    delete_vessel_assignment_handler,
    download_vessel_pdf_handler,
)
from routers.lambda_module.crew import (
    create_crew_handler,
    get_crew_handler,
    list_crew_handler,
    register_crew_handler,
    login_crew_handler,
    admin_reset_crew_password_handler,
    admin_delete_crew_handler,
    crew_me_handler,
    crew_dashboard_handler,
    crew_sync_handler,
)
from routers.lambda_module.inspection_form import (
    create_inspection_form_handler,
    get_inspection_form_handler,
    update_inspection_form_handler,
    delete_inspection_form_handler,
    list_inspection_forms_handler,
    list_submitted_forms_handler,
    list_inspector_forms_handler,
    submit_inspection_form_handler,
    list_template_forms_handler,
    get_template_form_handler,
    attach_template_form_handler,
)
from routers.lambda_module.inspection_assignment import (
    create_inspection_assignment_handler,
    bulk_create_inspection_assignment_handler,
    get_inspection_assignment_handler,
    list_inspection_assignments_handler,
    list_inspector_assignments_handler,
    create_crew_inspection_assignment_handler,
    list_crew_assignments_handler,
    delete_inspection_assignment_handler,
    download_inspection_pdf_handler,
    list_inspection_assignments_latest,
    update_inspection_assignment_handler,
    trigger_inspection_ai_analysis_handler,
    get_ai_analysis_progress_handler
)
from routers.lambda_module.defect import (
    list_defects_handler,
    get_defect_handler,
    approve_defect_handler,
    close_defect_handler,
    add_comment_handler,
    inspector_comment_handler,
    update_defect_handler,
    create_inspector_defect_handler,
    list_inspector_defects_handler,
    create_crew_defect_handler,
    list_crew_defects_handler,
    add_inspector_defect_analysis_handler,
    add_crew_defect_analysis_handler,
    crew_comment_handler,  # Added missing import
    download_defect_pdf_handler,  # Added missing import
)
from routers.lambda_module.notifications_handler import (
    create_notification_handler,
    list_notifications_handler,
    get_notification_handler,
    update_notification_handler,
    delete_notification_handler,
    mark_notification_read_handler,
    mark_multiple_notifications_read_handler,
    mark_all_notifications_read_handler,
    get_unread_count_handler
)
from routers.lambda_module.recurring_inspection_handler import trigger_recurring_inspections_handler
from routers.lambda_module.system_logs_handler import (
    create_system_log_handler,
    list_system_logs_handler,
    get_system_log_handler,
    update_system_log_status_handler,
    update_system_log_priority_handler,
)
from routers.lambda_module.company_notifications_handler import (
    create_company_notification_handler,
    list_company_notifications_handler,
    get_company_notification_handler,
    update_company_notification_handler,
    delete_company_notification_handler,
    mark_company_notification_read_handler,
    mark_multiple_company_notifications_read_handler,
    mark_all_company_notifications_read_handler,
    get_company_unread_count_handler
)
from routers.lambda_module.vessel_certificates import (
    create_certificate_handler,
    update_certificate_handler,
    delete_certificate_handler,
    get_certificate_handler,
    list_certificates_handler,
)

from routers.lambda_module.upload import presign_upload_handler
from routers.lambda_module.dashboard import get_dashboard_handler
from fastapi.responses import JSONResponse
import json
from utility.lambda_to_fastapi import lambda_to_fastapi_response
from utility.fastapi_response import lambda_response_to_fastapi
from utility.role_based_access_control import require_role
from fastapi import Depends
import base64
from decimal import Decimal

# Create main API router
api_router = APIRouter()
from fastapi.responses import JSONResponse
import json
from decimal import Decimal

def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj

def parse_lambda_response(result: dict):
    status_code = result.get("statusCode", 200)
    headers = result.get("headers", {})
    body = result.get("body")

    if result.get("isBase64Encoded") and body:
        decoded_body = base64.b64decode(body)
        return Response(
            content=decoded_body,
            status_code=status_code,
            headers=headers,
            media_type=headers.get("Content-Type", "application/octet-stream"),
        )
    
    if body is None:
        body = {k: v for k, v in result.items() if k not in ["statusCode", "headers", "cookies"]}

    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            body = {"raw": body}
            
    body = convert_decimals(body)

    response = JSONResponse(status_code=status_code, content=body, headers=headers)
    
    cookies = result.get("cookies", [])
    for cookie in cookies:
        parts = cookie.split(";")
        if not parts or "=" not in parts[0]:
            continue

        key, value = parts[0].split("=", 1)
        cookie_params = {
            p.split("=")[0].strip().lower(): (p.split("=")[1] if "=" in p else True)
            for p in parts[1:]
        }

        response.set_cookie(
            key=key,
            value=value,
            httponly=cookie_params.get("httponly", True),
            secure=cookie_params.get("secure", True),
            samesite=cookie_params.get("samesite", "None"),
            path=cookie_params.get("path", "/"),
        )

    return response

admin_admin_router = APIRouter(prefix="/admin/admin", tags=["Admin - Admin Management"])

@admin_admin_router.post("", summary="Create Admin (Admin)")
async def admin_create_admin_route(
    request: Request, 
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Admin creates a new admin with documents and password."""
    event = await lambda_to_fastapi_response(request)
    result = admin_create_admin_handler(event, None)
    return parse_lambda_response(result)

@admin_admin_router.get("", summary="List Admins (Admin)")
async def admin_list_admins_route(
    request: Request,
    page: int = Query(1),
    limit: int = Query(20),
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Admin lists all admins with pagination."""
    event = await lambda_to_fastapi_response(request, query_params={"page": str(page), "limit": str(limit)})
    result = admin_list_admins_handler(event, None)
    return parse_lambda_response(result)

@admin_admin_router.get("/{admin_id}", summary="Get Admin (Admin)")
async def admin_get_admin_route(
    admin_id: str, 
    request: Request,
    tenant_ctx = Depends(require_role("admin")), 
    authorization: Optional[str] = Header(None)
):
    """Admin gets admin details by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"admin_id": admin_id})
    result = admin_get_admin_handler(event, None)
    return parse_lambda_response(result)

@admin_admin_router.post("/{admin_id}/reset-password", summary="Reset Admin Password (Admin)")
async def admin_reset_admin_password_route(
    admin_id: str, 
    request: Request,
    tenant_ctx = Depends(require_role("admin")), 
    authorization: Optional[str] = Header(None)
):
    """Admin resets an admin's password."""
    event = await lambda_to_fastapi_response(request, path_params={"admin_id": admin_id})
    result = admin_reset_admin_password_handler(event, None)
    return parse_lambda_response(result)

@admin_admin_router.delete("/{admin_id}", summary="Delete Admin (Admin)")
async def admin_delete_admin_route(
    admin_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None),
):
    """
    Admin soft-deletes an admin by ID.
    """
    event = await lambda_to_fastapi_response(
        request,
        path_params={"admin_id": admin_id},
    )
    result = admin_delete_admin_handler(event, None)
    return parse_lambda_response(result)

@admin_admin_router.put("/{admin_id}", summary="Update Admin (Admin)")
async def admin_update_admin_route(
    admin_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Admin updates an admin's information."""
    event = await lambda_to_fastapi_response(
        request,
        path_params={"admin_id": admin_id}
    )
    result = admin_update_admin_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# INSPECTOR AUTHENTICATION ROUTES
# ============================================================================
inspector_router = APIRouter(prefix="/inspectors", tags=["Inspector Authentication"])

@inspector_router.post("/register", summary="Register Inspector")
async def register_inspector_route(request: Request):
    """Register a new inspector account."""
    event = await lambda_to_fastapi_response(request)
    result = inspector_register(event, None)
    return parse_lambda_response(result)

@inspector_router.post("/login", summary="Login Inspector")
async def login_inspector_route(request: Request, response: Response):
    """Login an existing inspector."""
    event = await lambda_to_fastapi_response(request)
    result = inspector_login(event, response)
    return parse_lambda_response(result)

@inspector_router.post(
    "/change-password", summary="Complete First-Login Password Change"
)
async def change_inspector_password_route(request: Request, response: Response):
    """Complete Cognito NEW_PASSWORD_REQUIRED challenge. Public — no auth cookie required."""
    event = await lambda_to_fastapi_response(request)
    result = inspector_change_password(event, response)
    return parse_lambda_response(result)  # Fixed: added parse_lambda_response

@inspector_router.get("/{inspector_id:uuid}", summary="Get Inspector Profile")
async def get_inspector_profile_route(inspector_id: str, request: Request, tenant_ctx = Depends(require_role("admin"))):
    """Get inspector profile by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"inspector_id": str(inspector_id)})
    result = inspector_profile(event, None)
    return parse_lambda_response(result)

@inspector_router.get("/dashboard", summary="Get Inspector Dashboard")
async def get_inspector_dashboard_route(request: Request, tenant_ctx = Depends(require_role("inspector")), authorization: Optional[str] = Header(None)):
    """Get dashboard data for the authenticated inspector."""   
    event = await lambda_to_fastapi_response(request)
    result = inspector_dashboard_handler(event, None)
    return parse_lambda_response(result)

@inspector_router.post("/sync", summary="Check Inspector Sync Status")
async def check_inspector_sync_route(request: Request, tenant_ctx = Depends(require_role("admin","inspector")), authorization: Optional[str] = Header(None)):
    """Check sync status for the authenticated inspector."""
    event = await lambda_to_fastapi_response(request)
    result = inspector_sync_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# INSPECTOR ME ROUTE (separate to avoid path conflicts)
# ============================================================================
inspector_me_router = APIRouter(prefix="/inspector", tags=["Inspector Authentication"])

@inspector_me_router.get("/me", summary="Get Current Inspector Profile")
async def get_current_inspector_route(request: Request, tenant_ctx = Depends(require_role("admin","inspector")), authorization: Optional[str] = Header(None)):
    """Get the currently authenticated inspector's profile."""
    event = await lambda_to_fastapi_response(request)
    result = inspector_me_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# ADMIN AUTHENTICATION ROUTES
# ============================================================================
admin_router = APIRouter(prefix="/admins", tags=["Admin Authentication"])

@admin_router.post("/register", summary="Register Admin")
async def register_admin_route(request: Request):
    """Register a new admin account."""
    event = await lambda_to_fastapi_response(request)
    result = admin_register_handler(event, None)
    return parse_lambda_response(result)

@admin_router.post("/login", summary="Login Admin")
async def login_admin_route(request: Request, response: Response):
    """Login an existing admin."""
    event = await lambda_to_fastapi_response(request)
    result = admin_login_handler(event, response)
    return parse_lambda_response(result)

@admin_router.post("/change-password", summary="Complete First-Login Password Change")
async def change_password_admin_route(request: Request, response: Response):
    """
    Respond to Cognito NEW_PASSWORD_REQUIRED challenge.
    Call this when login returns requires_new_password=True.
    """
    event = await lambda_to_fastapi_response(request)
    result = admin_change_password_handler(event, response)
    return parse_lambda_response(result)

@admin_router.get("/{admin_id}", summary="Get Admin Profile")
async def get_admin_profile_route(admin_id: str, request: Request, tenant_ctx = Depends(require_role("admin"))):
    """Get admin profile by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"admin_id": admin_id})
    result = admin_profile_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# ADMIN PROFILE ROUTE (separate prefix)
# ============================================================================
admin_profile_router = APIRouter(prefix="/admin", tags=["Admin Authentication"])

@admin_profile_router.get("/profile", summary="Get Current Admin Profile")
async def get_current_admin_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Get the currently authenticated admin's profile."""
    event = await lambda_to_fastapi_response(request)
    result = admin_me_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# ADMIN INSPECTOR MANAGEMENT ROUTES
# ============================================================================
admin_inspector_router = APIRouter(prefix="/admin/inspectors", tags=["Admin - Inspector Management"])

@admin_inspector_router.post("", summary="Create Inspector (Admin)")
async def admin_create_inspector_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Admin creates a new inspector with documents and password."""
    event = await lambda_to_fastapi_response(request)
    result = admin_create_inspector_handler(event, None)
    return parse_lambda_response(result)

@admin_inspector_router.get("", summary="List Inspectors (Admin)")
async def admin_list_inspectors_route(
    request: Request,
    page: int = Query(1),
    limit: int = Query(20),
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Admin lists all inspectors with pagination."""
    event = await lambda_to_fastapi_response(request, query_params={"page": str(page), "limit": str(limit)})
    result = admin_list_inspectors_handler(event, None)
    return parse_lambda_response(result)

@admin_inspector_router.get("/{inspector_id}", summary="Get Inspector (Admin)")
async def admin_get_inspector_route(inspector_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Admin gets inspector details by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"inspector_id": inspector_id})
    result = admin_get_inspector_handler(event, None)
    return parse_lambda_response(result)

@admin_inspector_router.post("/{inspector_id}/reset-password", summary="Reset Inspector Password (Admin)")
async def admin_reset_inspector_password_route(inspector_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Admin resets an inspector's password."""
    event = await lambda_to_fastapi_response(request, path_params={"inspector_id": inspector_id})
    result = admin_reset_inspector_password_handler(event, None)
    return parse_lambda_response(result)

@admin_inspector_router.delete("/{inspector_id}", summary="Delete Inspector (Admin)")
async def admin_delete_inspector_route(
    inspector_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None),
):
    """
    Admin soft-deletes an inspector by ID.
    """
    event = await lambda_to_fastapi_response(
        request,
        path_params={"inspector_id": inspector_id},
    )
    result = admin_delete_inspector_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# VESSEL MANAGEMENT ROUTES
# ============================================================================
vessel_router = APIRouter(prefix="/vessels", tags=["Vessel Management"])

@vessel_router.post("", summary="Create Vessel")
async def create_vessel_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Create a new vessel (admin only)."""
    event = await lambda_to_fastapi_response(request)
    result = create_vessel_handler(event, None)
    return parse_lambda_response(result)

@vessel_router.get("", summary="List Vessels")
async def list_vessels_route(
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    page: int = Query(1),
    limit: int = Query(20),
    authorization: Optional[str] = Header(None)
):
    """List all vessels for the authenticated admin with pagination."""
    event = await lambda_to_fastapi_response(request, query_params={"page": str(page), "limit": str(limit)})
    result = list_vessels_handler(event, None)
    return parse_lambda_response(result)

@vessel_router.get("/{vessel_id}", summary="Get Vessel")
async def get_vessel_route(vessel_id: str, request: Request, tenant_ctx = Depends(require_role("admin"))):
    """Get a single vessel by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id})
    result = get_vessel_handler(event, None)
    return parse_lambda_response(result)

@vessel_router.post("/assignments", summary="Create Vessel Assignment")
async def create_vessel_assignment_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Assign a crew member or inspector to a vessel (admin only)."""
    event = await lambda_to_fastapi_response(request)
    result = create_vessel_assignment_handler(event, None)
    return parse_lambda_response(result)

@vessel_router.get("/assignments/{vessel_id}", summary="Get Vessel Assignments")
async def get_vessel_assignments_route(vessel_id: str, request: Request, tenant_ctx = Depends(require_role("admin"))):
    """Get all assignments (crew and inspectors) for a vessel."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id})
    result = get_vessel_assignments_handler(event, None)
    return parse_lambda_response(result)

@vessel_router.delete(
    "/assignments/{vessel_id}/{assignment_id}",
    summary="Delete Vessel Assignment",
)
async def delete_vessel_assignment_route(
    vessel_id: str,
    assignment_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin"))
):
    """Delete a vessel assignment by vessel_id and assignment_id (admin only)."""
    event = await lambda_to_fastapi_response(
        request,
        path_params={
            "vessel_id": vessel_id,
            "assignment_id": assignment_id,
        },
    )
    result = delete_vessel_assignment_handler(event, None)
    return parse_lambda_response(result)

@vessel_router.get("/{vessel_id}/download", summary="Download Vessel PDF")
async def download_vessel_pdf_route(vessel_id: str, request: Request, tenant_ctx = Depends(require_role("admin"))):
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id})
    result = download_vessel_pdf_handler(event, None)
    return parse_lambda_response(result)

# Added missing vessel defect PDF download route
@vessel_router.get(
    "/{vessel_id}/defects/pdf", summary="Download Vessel Defect Report PDF"
)
async def download_defect_pdf_route(
    vessel_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin", "inspector")),
):
    event = await lambda_to_fastapi_response(
        request, path_params={"vessel_id": vessel_id}
    )
    result = download_defect_pdf_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# CREW MANAGEMENT ROUTES
# ============================================================================
crew_router = APIRouter(prefix="/crew", tags=["Crew Management"])

@crew_router.post("", summary="Create Crew Member")
async def create_crew_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Create a new crew member (admin only)."""
    event = await lambda_to_fastapi_response(request)
    result = create_crew_handler(event, None)
    return parse_lambda_response(result)

@crew_router.delete("/{crew_id}", summary="Delete Crew Member (Admin)")
async def admin_delete_crew_route(crew_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Admin deletes (soft delete) a crew member by ID."""
    print("crew_id----------------------", crew_id)
    event = await lambda_to_fastapi_response(request, path_params={"crew_id": crew_id})
    result = admin_delete_crew_handler(event, None)
    return parse_lambda_response(result)

@crew_router.get("", summary="List Crew Members")
async def list_crew_route(
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    page: int = Query(1),
    limit: int = Query(20),
    authorization: Optional[str] = Header(None)
):
    """List all crew members with pagination (admin only)."""
    event = await lambda_to_fastapi_response(request, query_params={"page": str(page), "limit": str(limit)})
    result = list_crew_handler(event, None)
    return parse_lambda_response(result)

@crew_router.get("/{crew_id}", summary="Get Crew Member")
async def get_crew_route(crew_id: str, request: Request, tenant_ctx = Depends(require_role("admin","crew"))):
    """Get crew member details by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"crew_id": crew_id})
    result = get_crew_handler(event, None)
    return parse_lambda_response(result)

@crew_router.post("/register", summary="Register Crew Member")
async def register_crew_route(request: Request, tenant_ctx = Depends(require_role("admin","crew"))):
    """Register a new crew member account."""
    event = await lambda_to_fastapi_response(request)
    result = register_crew_handler(event, None)
    return parse_lambda_response(result)

@crew_router.post("/login", summary="Login Crew Member")
async def login_crew_route(request: Request, tenant_ctx = Depends(require_role("crew"))):
    """Login an existing crew member."""
    event = await lambda_to_fastapi_response(request)
    result = login_crew_handler(event, None)
    return parse_lambda_response(result)

@crew_router.get("/me", summary="Get Current Crew Profile")
async def get_current_crew_route(request: Request, tenant_ctx = Depends(require_role("admin","crew")), authorization: Optional[str] = Header(None)):
    """Get the currently authenticated crew member's profile."""
    event = await lambda_to_fastapi_response(request)
    result = crew_me_handler(event, None)
    return parse_lambda_response(result)

@crew_router.get("/dashboard", summary="Get Crew Dashboard")
async def get_crew_dashboard_route(request: Request, tenant_ctx = Depends(require_role("crew")), authorization: Optional[str] = Header(None)):
    """Get dashboard data for the authenticated crew member."""
    event = await lambda_to_fastapi_response(request)
    result = crew_dashboard_handler(event, None)
    return parse_lambda_response(result)

@crew_router.post("/sync", summary="Check Crew Sync Status")
async def check_crew_sync_route(request: Request, tenant_ctx = Depends(require_role("crew")), authorization: Optional[str] = Header(None)):
    """Check sync status for the authenticated crew member."""
    event = await lambda_to_fastapi_response(request)
    result = crew_sync_handler(event, None)
    return parse_lambda_response(result)

@crew_router.get("/assignments", summary="List Crew Assignments")
async def list_crew_assignments_route(request: Request, tenant_ctx = Depends(require_role("admin","crew")), authorization: Optional[str] = Header(None)):
    """List inspection assignments for the authenticated crew member."""
    event = await lambda_to_fastapi_response(request)
    result = list_crew_assignments_handler(event, None)
    return parse_lambda_response(result)

@crew_router.post("/{crew_id}/inspection-assignments", summary="Create Crew Inspection Assignment")
async def create_crew_inspection_assignment_route(crew_id: str, request: Request, tenant_ctx = Depends(require_role("admin","crew")), authorization: Optional[str] = Header(None)):
    """Create a single inspection assignment to a crew member."""
    event = await lambda_to_fastapi_response(request, path_params={"crew_id": crew_id})
    result = create_crew_inspection_assignment_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# CREW FORM ROUTES (Added missing router)
# ============================================================================
crew_form_router = APIRouter(prefix="/crew/forms", tags=["Crew - Inspection Forms"])

@crew_form_router.get("", summary="List Crew Forms")
async def list_crew_forms_route(
    request: Request,
    tenant_ctx=Depends(require_role("crew")),
    authorization: Optional[str] = Header(None),
):
    """List inspection forms assigned to the authenticated crew member."""
    event = await lambda_to_fastapi_response(request)
    result = list_inspector_forms_handler(event, None)
    return parse_lambda_response(result)

@crew_form_router.post(
    "/{vessel_id}/{form_id}/submit", summary="Submit Inspection Form (Crew)"
)
async def crew_submit_form_route(
    vessel_id: str,
    form_id: str,
    request: Request,
    tenant_ctx=Depends(require_role("crew")),
    authorization: Optional[str] = Header(None),
):
    """Submit/fill an inspection form by the authenticated crew member."""
    event = await lambda_to_fastapi_response(
        request, path_params={"vessel_id": vessel_id, "form_id": form_id}
    )
    result = submit_inspection_form_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# ADMIN CREW ROUTES
# ============================================================================
admin_crew_router = APIRouter(prefix="/admin/crew", tags=["Admin - Crew Management"])

@admin_crew_router.post("/{crew_id}/reset-password", summary="Reset Crew Password (Admin)")
async def admin_reset_crew_password_route(crew_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Admin resets a crew member's password."""
    event = await lambda_to_fastapi_response(request, path_params={"crew_id": crew_id})
    result = admin_reset_crew_password_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# INSPECTION FORM ROUTES
# ============================================================================
form_router = APIRouter(prefix="/forms", tags=["Inspection Forms"])

@form_router.post("", summary="Create Inspection Form")
async def create_form_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Create a new inspection form with ordered questions."""
    event = await lambda_to_fastapi_response(request)
    result = create_inspection_form_handler(event, None)
    return parse_lambda_response(result)

@form_router.get("", summary="List Inspection Forms")
async def list_forms_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """List inspection forms with pagination."""
    event = await lambda_to_fastapi_response(request)
    result = list_inspection_forms_handler(event, None)
    return parse_lambda_response(result)

@form_router.get("/templates", summary="List Templates Forms")
async def list_templates_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """List Templates forms with pagination."""
    event = await lambda_to_fastapi_response(request)
    result = list_template_forms_handler(event, None)
    return parse_lambda_response(result)

@form_router.get("/template/{template_name}", summary="Get Template Form")
async def get_template_route(template_name: str, request: Request=None, tenant_ctx = Depends(require_role("admin","inspector","crew"))):
    """Get template form by Name."""
    event = await lambda_to_fastapi_response(request, path_params={"title": template_name})
    result = get_template_form_handler(event, None)
    return parse_lambda_response(result)

@form_router.post("/attach-template", summary="Attach Template Form")
async def attach_template_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """attach a new form with ordered questions."""
    event = await lambda_to_fastapi_response(request)
    result = attach_template_form_handler(event, None)
    return parse_lambda_response(result)

@form_router.get("/{form_id}", summary="Get Inspection Form")
async def get_form_route(form_id: str,vessel_id: Optional[str] = Query(None), inspection_id: Optional[str] = Query(None), request: Request=None, tenant_ctx = Depends(require_role("admin","inspector","crew"))):
    """Get inspection form by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"form_id": form_id}, query_params={"vessel_id": vessel_id,"inspection_id": inspection_id})
    result = get_inspection_form_handler(event, None)
    return parse_lambda_response(result)

@form_router.put("/{form_id}", summary="Update Inspection Form")
async def update_form_route(
    form_id: str, 
    request: Request, 
    tenant_ctx = Depends(require_role("admin")),  # Fixed: moved Depends to correct position
    authorization: Optional[str] = Header(None)
):
    """Update inspection form by ID (admin only)."""
    event = await lambda_to_fastapi_response(request, path_params={"form_id": form_id})
    result = update_inspection_form_handler(event, None)
    return parse_lambda_response(result)

@form_router.delete("/{form_id}", summary="Delete Inspection Form")
async def delete_form_route(form_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Deactivate an inspection form by ID (admin only)."""
    event = await lambda_to_fastapi_response(request, path_params={"form_id": form_id})
    result = delete_inspection_form_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# INSPECTOR FORM ROUTES
# ============================================================================
inspector_form_router = APIRouter(prefix="/inspectors/forms", tags=["Inspector - Inspection Forms"])

@inspector_form_router.get("", summary="List Inspector Forms")
async def list_inspector_forms_route(request: Request, tenant_ctx = Depends(require_role("admin","inspector")), authorization: Optional[str] = Header(None)):
    """List inspection forms assigned to the authenticated inspector."""
    event = await lambda_to_fastapi_response(request)
    result = list_inspector_forms_handler(event, None)
    return parse_lambda_response(result)

@inspector_form_router.post("/{vessel_id}/{form_id}/submit", summary="Submit Inspection Form")
async def submit_form_route(vessel_id: str, form_id: str, request: Request, tenant_ctx = Depends(require_role("admin","inspector")), authorization: Optional[str] = Header(None)):
    """Submit/fill an inspection form by the authenticated inspector."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "form_id": form_id})
    result = submit_inspection_form_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# ADMIN FORM ROUTES
# ============================================================================
admin_form_router = APIRouter(prefix="/admin/forms", tags=["Admin - Inspection Forms"])

@admin_form_router.get("/submitted", summary="List Submitted Forms (Admin)")
async def list_submitted_forms_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """List submitted (Closed) forms with answers for admin view."""
    event = await lambda_to_fastapi_response(request)
    result = list_submitted_forms_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# INSPECTION ASSIGNMENT ROUTES
# ============================================================================
assignment_router = APIRouter(prefix="/inspection-assignments", tags=["Inspection Assignments"])

@assignment_router.post("", summary="Create Inspection Assignment")
async def create_assignment_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Create a new inspection assignment."""
    event = await lambda_to_fastapi_response(request)
    result = create_inspection_assignment_handler(event, None)
    return parse_lambda_response(result)

@assignment_router.post("/bulk", summary="Bulk Create Inspection Assignments")
async def bulk_create_assignment_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Create multiple inspection assignments to an inspector."""
    event = await lambda_to_fastapi_response(request)
    result = bulk_create_inspection_assignment_handler(event, None)
    return parse_lambda_response(result)

@assignment_router.get("", summary="List Inspection Assignments")
async def list_assignments_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """List inspection assignments with pagination."""
    event = await lambda_to_fastapi_response(request)
    result = list_inspection_assignments_handler(event, None)
    return parse_lambda_response(result)

@assignment_router.get("/latest", summary="List Inspection Assignments latest")
async def list_assignments_latest_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """List inspection assignments with pagination latest."""
    event = await lambda_to_fastapi_response(request)
    result = list_inspection_assignments_latest(event, None)
    return parse_lambda_response(result)

@assignment_router.put("/{vessel_id}/{assignment_id}", summary="Update Inspection Assignment")
async def update_assignment_route(
    request: Request,
    vessel_id: str,
    assignment_id: str,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Update an existing inspection assignment."""
    event = await lambda_to_fastapi_response(request)
    # Add path parameters to event
    event["pathParameters"] = {
        "vessel_id": vessel_id,
        "assignment_id": assignment_id
    }
    result = update_inspection_assignment_handler(event, None)
    return parse_lambda_response(result)

# Added missing assignment download by ID route
@assignment_router.get("/{assignment_id}/download-pdf", summary="Download Inspection Report PDF")
async def download_inspection_pdf_route_by_id(
    assignment_id: str,
    request: Request,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None),
):
    """Generate inspection PDF, upload to S3, and return a presigned download URL."""
    event = await lambda_to_fastapi_response(
        request, path_params={"assignment_id": assignment_id}
    )
    result = download_inspection_pdf_handler(event, None)
    return parse_lambda_response(result)

@assignment_router.get("/{vessel_id}/{assignment_id}", summary="Get Inspection Assignment")
async def get_assignment_route(vessel_id: str, assignment_id: str, request: Request, tenant_ctx = Depends(require_role("admin"))):
    """Get inspection assignment by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "assignment_id": assignment_id})
    result = get_inspection_assignment_handler(event, None)
    return parse_lambda_response(result)

@assignment_router.delete("/{vessel_id}/{assignment_id}/{form_id}", summary="Delete Inspection Assignment")
async def delete_assignment_route(vessel_id: str, assignment_id: str, form_id: str, request: Request, tenant_ctx = Depends(require_role("admin"))):
    """Remove a form from its assignment by form_id."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "assignment_id": assignment_id, "form_id": form_id})
    result = delete_inspection_assignment_handler(event, None)
    return parse_lambda_response(result)

@assignment_router.get("/{vessel_id}/{assignment_id}/download", summary="Download Inspection Report PDF")
async def download_inspection_pdf_route(vessel_id: str, assignment_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Download inspection report as PDF."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "assignment_id": assignment_id})
    result = await download_inspection_pdf_handler(event, None)
    return parse_lambda_response(result)

@assignment_router.post("/{vessel_id}/{assignment_id}/ai-analysis", summary="Trigger AI Analysis for Inspection")
async def trigger_ai_analysis_route(
    request: Request,
    vessel_id: str,
    assignment_id: str,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Trigger AI analysis for all questions in an inspection."""
    event = await lambda_to_fastapi_response(request)
    event["pathParameters"] = {
        "vessel_id": vessel_id,
        "assignment_id": assignment_id
    }
    result = trigger_inspection_ai_analysis_handler(event, None)
    return parse_lambda_response(result)

@assignment_router.get("/{vessel_id}/{assignment_id}/ai-analysis/progress", summary="Get AI Analysis Progress")
async def get_ai_analysis_progress_route(
    request: Request,
    vessel_id: str,
    assignment_id: str,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Get progress of AI analysis for an inspection."""
    event = await lambda_to_fastapi_response(request)
    event["pathParameters"] = {
        "vessel_id": vessel_id,
        "assignment_id": assignment_id
    }
    result = get_ai_analysis_progress_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# INSPECTOR ASSIGNMENT ROUTES
# ============================================================================
inspector_assignment_router = APIRouter(prefix="/inspectors/assignments", tags=["Inspector - Assignments"])

@inspector_assignment_router.get("", summary="List Inspector Assignments")
async def list_inspector_assignments_route(request: Request, tenant_ctx = Depends(require_role("admin","inspector")), authorization: Optional[str] = Header(None)):
    """List inspection assignments for the authenticated inspector."""
    event = await lambda_to_fastapi_response(request)
    result = list_inspector_assignments_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# DEFECT MANAGEMENT ROUTES (ADMIN)
# ============================================================================
admin_defect_router = APIRouter(prefix="/admin/defects", tags=["Admin - Defect Management"])

@admin_defect_router.get("", summary="List Defects (Admin)")
async def list_defects_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """List defects with pagination and optional filtering."""
    event = await lambda_to_fastapi_response(request)
    result = list_defects_handler(event, None)
    return parse_lambda_response(result)

@admin_defect_router.get("/{vessel_id}/{defect_id}", summary="Get Defect (Admin)")
async def get_defect_route(vessel_id: str, defect_id: str, request: Request, tenant_ctx = Depends(require_role("admin"))):
    """Get defect by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "defect_id": defect_id})
    result = get_defect_handler(event, None)
    return parse_lambda_response(result)

@admin_defect_router.post("/{vessel_id}/{defect_id}/approve", summary="Approve Defect Resolution")
async def approve_defect_route(vessel_id: str, defect_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Approve defect resolution."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "defect_id": defect_id})
    result = approve_defect_handler(event, None)
    return parse_lambda_response(result)

@admin_defect_router.post("/{vessel_id}/{defect_id}/close", summary="Close Defect")
async def close_defect_route(vessel_id: str, defect_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Close defect."""
    print("hitted this")
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "defect_id": defect_id})
    result = close_defect_handler(event, None)
    return parse_lambda_response(result)

@admin_defect_router.post("/{vessel_id}/{defect_id}/comments", summary="Add Defect Comment")
async def add_defect_comment_route(vessel_id: str, defect_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Add admin comment to defect."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "defect_id": defect_id})
    result = add_comment_handler(event, None)
    return parse_lambda_response(result)

@admin_defect_router.put("{vessel_id}/{defect_id}", summary="Update Defect")
async def update_defect_route(vessel_id: str, defect_id: str, request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Update defect fields."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "defect_id": defect_id})
    result = update_defect_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# INSPECTOR DEFECT ROUTES
# ============================================================================
inspector_defect_router = APIRouter(prefix="/inspectors/defects", tags=["Inspector - Defects"])

@inspector_defect_router.post("", summary="Create Defect (Inspector)")
async def create_inspector_defect_route(request: Request, tenant_ctx = Depends(require_role("admin","inspector")), authorization: Optional[str] = Header(None)):
    """Inspector creates a new defect from the mobile/web app."""
    event = await lambda_to_fastapi_response(request)
    result = create_inspector_defect_handler(event, None)
    return parse_lambda_response(result)

@inspector_defect_router.get("", summary="List Inspector Defects")
async def list_inspector_defects_route(request: Request, tenant_ctx = Depends(require_role("admin","inspector")), authorization: Optional[str] = Header(None)):
    """List defects raised by the authenticated inspector."""
    event = await lambda_to_fastapi_response(request)
    result = list_inspector_defects_handler(event, None)
    return parse_lambda_response(result)

@inspector_defect_router.post("/{vessel_id}/{defect_id}/analysis", summary="Add Defect Analysis (Inspector)")
async def add_inspector_defect_analysis_route(vessel_id: str, defect_id: str, request: Request, tenant_ctx = Depends(require_role("admin","inspector")), authorization: Optional[str] = Header(None)):
    """Add or update defect analysis for a defect by the authenticated inspector."""  
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "defect_id": defect_id})
    result = add_inspector_defect_analysis_handler(event, None)
    return parse_lambda_response(result)

@inspector_defect_router.post("/{vessel_id}/{defect_id}/comments", summary="Add Defect Comment")
async def inpector_defect_comment_route(vessel_id: str, defect_id: str, request: Request, tenant_ctx = Depends(require_role("admin","inspector")), authorization: Optional[str] = Header(None)):
    """Add inspector comment to defect."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "defect_id": defect_id})
    result = inspector_comment_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# CREW DEFECT ROUTES
# ============================================================================
crew_defect_router = APIRouter(prefix="/crew/defects", tags=["Crew - Defects"])

@crew_defect_router.post("", summary="Create Defect (Crew)")
async def create_crew_defect_route(request: Request, tenant_ctx = Depends(require_role("admin","crew")), authorization: Optional[str] = Header(None)):
    """Crew creates a new defect from the mobile app."""
    event = await lambda_to_fastapi_response(request)
    result = create_crew_defect_handler(event, None)
    return parse_lambda_response(result)

@crew_defect_router.get("", summary="List Crew Defects")
async def list_crew_defects_route(request: Request, tenant_ctx = Depends(require_role("admin","crew")), authorization: Optional[str] = Header(None)):
    """List defects raised by the authenticated crew member."""
    event = await lambda_to_fastapi_response(request)
    result = list_crew_defects_handler(event, None)
    return parse_lambda_response(result)

# Added missing crew defect comment route
@crew_defect_router.post("/{vessel_id}/{defect_id}/comments", summary="Add Defect Comment (Crew)")
async def crew_defect_comment_route(
    vessel_id: str,
    defect_id: str,
    request: Request,
    tenant_ctx=Depends(require_role("crew")),
    authorization: Optional[str] = Header(None),
):
    """Add crew comment to defect."""
    event = await lambda_to_fastapi_response(
        request, path_params={"vessel_id": vessel_id, "defect_id": defect_id}
    )
    result = crew_comment_handler(event, None)
    return parse_lambda_response(result)

@crew_defect_router.post("/{vessel_id}/{defect_id}/analysis", summary="Add Defect Analysis (Crew)")
async def add_crew_defect_analysis_route(vessel_id: str, defect_id: str, request: Request, tenant_ctx = Depends(require_role("admin","crew")), authorization: Optional[str] = Header(None)):
    """Add or update defect analysis for a defect by the authenticated crew member."""
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id, "defect_id": defect_id})
    result = add_crew_defect_analysis_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# UPLOAD ROUTES
# ============================================================================
upload_router = APIRouter(prefix="/uploads", tags=["File Upload"])

@upload_router.post("/presign", summary="Get Presigned Upload URL")
async def presign_upload_route(request: Request, tenant_ctx = Depends(require_role("admin","inspector","crew")), authorization: Optional[str] = Header(None)):
    """Get a presigned URL for uploading files to S3."""
    event = await lambda_to_fastapi_response(request)
    result = presign_upload_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# DASHBOARD ROUTES
# ============================================================================
dashboard_router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])

@dashboard_router.get("", summary="Get Admin Dashboard")
async def get_dashboard_route(request: Request, tenant_ctx = Depends(require_role("admin")), authorization: Optional[str] = Header(None)):
    """Get dashboard data for the authenticated admin."""
    event = await lambda_to_fastapi_response(request)
    result = get_dashboard_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# NOTIFICATIONS ROUTES
# ============================================================================
notifications_router = APIRouter(prefix="/notifications", tags=["Admin - Notifications"])

@notifications_router.get("", summary="Get notifications")
async def get_notifications_route(
    request: Request,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Get notifications for the authenticated admin."""
    event = await lambda_to_fastapi_response(request)
    result = list_notifications_handler(event, None)
    return parse_lambda_response(result)

@notifications_router.get("/unread-count", summary="Get unread notifications count")
async def get_unread_count_route(
    request: Request,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Get unread notifications count for the authenticated admin."""
    event = await lambda_to_fastapi_response(request)
    result = get_unread_count_handler(event, None)
    return parse_lambda_response(result)

@notifications_router.get("/{notification_id}", summary="Get notification by ID")
async def get_notification_route(
    request: Request,
    notification_id: str,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Get a specific notification by ID."""
    event = await lambda_to_fastapi_response(request)
    result = get_notification_handler(event, None)
    return parse_lambda_response(result)

@notifications_router.post("", summary="Create notification")
async def create_notification_route(
    request: Request,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Create a new notification (admin only)."""
    event = await lambda_to_fastapi_response(request)
    result = create_notification_handler(event, None)
    return parse_lambda_response(result)

@notifications_router.put("/{notification_id}", summary="Update notification")
async def update_notification_route(
    request: Request,
    notification_id: str,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Update a notification by ID (admin only)."""
    event = await lambda_to_fastapi_response(request)
    result = update_notification_handler(event, None)
    return parse_lambda_response(result)

@notifications_router.delete("/{notification_id}", summary="Delete notification")
async def delete_notification_route(
    request: Request,
    notification_id: str,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Delete a notification by ID (admin only)."""
    event = await lambda_to_fastapi_response(request)
    result = delete_notification_handler(event, None)
    return parse_lambda_response(result)

@notifications_router.post("/{notification_id}/read", summary="Mark notification as read")
async def mark_notification_read_route(
    request: Request,
    notification_id: str,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Mark a specific notification as read."""
    event = await lambda_to_fastapi_response(request)
    result = mark_notification_read_handler(event, None)
    return parse_lambda_response(result)

@notifications_router.post("/mark-read", summary="Mark multiple notifications as read")
async def mark_multiple_notifications_read_route(
    request: Request,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Mark multiple notifications as read."""
    event = await lambda_to_fastapi_response(request)
    result = mark_multiple_notifications_read_handler(event, None)
    return parse_lambda_response(result)

@notifications_router.post("/mark-all-read", summary="Mark all notifications as read")
async def mark_all_notifications_read_route(
    request: Request,
    tenant_ctx=Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Mark all notifications as read for the current user."""
    event = await lambda_to_fastapi_response(request)
    result = mark_all_notifications_read_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# Recurring Inspection ROUTES
# ============================================================================
recurring_inspection_router = APIRouter(prefix="/admin/recurring-inspections", tags=["Admin - Recurring Inspections"])

@recurring_inspection_router.post("/trigger", summary="Trigger Recurring Inspections Manually")
async def trigger_recurring_route(
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Manually trigger recurring inspection scheduler to create new assignments for due forms."""
    event = await lambda_to_fastapi_response(request)
    result = trigger_recurring_inspections_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# SYSTEM LOGS MANAGEMENT ROUTES
# ============================================================================
system_logs_router = APIRouter(prefix="/system-logs", tags=["System Logs Management"])

@system_logs_router.post("", summary="Create System Log")
async def create_system_log_route(
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """Create a new system log (admin only)."""
    print("hitted----------------------------")
    event = await lambda_to_fastapi_response(request)
    result = create_system_log_handler(event, None)
    return parse_lambda_response(result)

@system_logs_router.get("", summary="List System Logs")
async def list_system_logs_route(
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    page: int = Query(1),
    limit: int = Query(20),
    authorization: Optional[str] = Header(None)
):
    """List all system logs for the authenticated admin with pagination."""
    event = await lambda_to_fastapi_response(request, query_params={"page": str(page), "limit": str(limit)})
    result = list_system_logs_handler(event, None)
    return parse_lambda_response(result)

@system_logs_router.get("/{log_id}", summary="Get System Log")
async def get_system_log_route(
    log_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin"))
):
    """Get a single system log by ID."""
    event = await lambda_to_fastapi_response(request, path_params={"log_id": log_id})
    result = get_system_log_handler(event, None)
    return parse_lambda_response(result)

@system_logs_router.patch("/{log_id}/status", summary="Update System Log Status")
async def update_system_log_status_route(
    log_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin"))
):
    """Update system log status (admin only)."""
    event = await lambda_to_fastapi_response(request, path_params={"log_id": log_id})
    result = update_system_log_status_handler(event, None)
    return parse_lambda_response(result)

@system_logs_router.patch("/{log_id}/priority", summary="Update System Log Priority")
async def update_system_log_priority_route(
    log_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin"))
):
    """Update system log priority (admin only)."""
    event = await lambda_to_fastapi_response(request, path_params={"log_id": log_id})
    result = update_system_log_priority_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# Company specific Notifications ROUTES
# ============================================================================
company_notifications_router = APIRouter(prefix="/company-notifications", tags=["Company Notifications"])

@company_notifications_router.get("")
async def get_my_notifications(
    request: Request,
    page: int = 1,
    limit: int = 20,
    tenant_ctx=Depends(require_role("admin", "inspector", "crew")),
    authorization: Optional[str] = Header(None)
):
    """
    Get notifications based on user type:
    - Admin: Gets ALL notifications (no filtering)
    - Inspector: Gets ADMIN notifications where they are in recipients or ALL
    - Crew: Gets ADMIN notifications where they are in recipients or ALL
    """
    # Add query params to request
    request.scope["query_string"] = f"page={page}&limit={limit}".encode()
    event = await lambda_to_fastapi_response(request)
    result = list_company_notifications_handler(event, None)
    return parse_lambda_response(result)

@company_notifications_router.get("/unread-count")
async def get_unread_count(
    request: Request,
    tenant_ctx=Depends(require_role("admin", "inspector", "crew")),
    authorization: Optional[str] = Header(None)
):
    """Get unread notifications count for the authenticated user."""
    event = await lambda_to_fastapi_response(request)
    result = get_company_unread_count_handler(event, None)
    return parse_lambda_response(result)

@company_notifications_router.get("/{notification_id}")
async def get_notification_by_id(
    request: Request,
    notification_id: str,
    tenant_ctx=Depends(require_role("admin", "inspector", "crew")),
    authorization: Optional[str] = Header(None)
):
    """Get a specific notification by ID with access control based on user type."""
    # Add path param to request
    request.scope["path_parameters"] = {"notification_id": notification_id}
    event = await lambda_to_fastapi_response(request)
    result = get_company_notification_handler(event, None)
    return parse_lambda_response(result)

@company_notifications_router.post("")
async def create_notification(
    request: Request,
    tenant_ctx=Depends(require_role("admin", "inspector", "crew")),
    authorization: Optional[str] = Header(None)
):
    """Create a new notification. All users can create notifications."""
    event = await lambda_to_fastapi_response(request)
    result = create_company_notification_handler(event, None)
    return parse_lambda_response(result)

@company_notifications_router.put("/{notification_id}")
async def update_notification(
    request: Request,
    notification_id: str,
    tenant_ctx=Depends(require_role("admin", "inspector", "crew")),
    authorization: Optional[str] = Header(None)
):
    """Update a notification by ID (only creator can update)."""
    # Add path param to request
    request.scope["path_parameters"] = {"notification_id": notification_id}
    event = await lambda_to_fastapi_response(request)
    result = update_company_notification_handler(event, None)
    return parse_lambda_response(result)

@company_notifications_router.delete("/{notification_id}")
async def delete_notification(
    request: Request,
    notification_id: str,
    tenant_ctx=Depends(require_role("admin", "inspector", "crew")),
    authorization: Optional[str] = Header(None)
):
    """Delete a notification by ID (only creator can delete)."""
    # Add path param to request
    request.scope["path_parameters"] = {"notification_id": notification_id}
    event = await lambda_to_fastapi_response(request)
    result = delete_company_notification_handler(event, None)
    return parse_lambda_response(result)

@company_notifications_router.post("/{notification_id}/read")
async def mark_notification_read(
    request: Request,
    notification_id: str,
    tenant_ctx=Depends(require_role("admin", "inspector", "crew")),
    authorization: Optional[str] = Header(None)
):
    """Mark a specific notification as read."""
    # Add path param to request
    request.scope["path_parameters"] = {"notification_id": notification_id}
    event = await lambda_to_fastapi_response(request)
    result = mark_company_notification_read_handler(event, None)
    return parse_lambda_response(result)

@company_notifications_router.post("/mark-read")
async def mark_multiple_notifications_read(
    request: Request,
    tenant_ctx=Depends(require_role("admin", "inspector", "crew")),
    authorization: Optional[str] = Header(None)
):
    """Mark multiple notifications as read. Send JSON body with notification_ids list."""
    event = await lambda_to_fastapi_response(request)
    result = mark_multiple_company_notifications_read_handler(event, None)
    return parse_lambda_response(result)

@company_notifications_router.post("/mark-all-read")
async def mark_all_notifications_read(
    request: Request,
    tenant_ctx=Depends(require_role("admin", "inspector", "crew")),
    authorization: Optional[str] = Header(None)
):
    """Mark all notifications as read for the current user."""
    event = await lambda_to_fastapi_response(request)
    result = mark_all_company_notifications_read_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# VESSEL CERTIFICATE ROUTES
# ============================================================================
certificate_router = APIRouter(prefix="/vessel/{vessel_id}/certificates", tags=["Vessel Certificates"])

@certificate_router.post("", summary="Create Certificate")
async def create_certificate_route(
    vessel_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """
    Create a new certificate for a vessel (admin only).
    Supports multipart/form-data for file uploads.
    """
    event = await lambda_to_fastapi_response(request, path_params={"vessel_id": vessel_id})
    result = create_certificate_handler(event, None)
    return parse_lambda_response(result)

@certificate_router.get("", summary="List Certificates")
async def list_certificates_route(
    vessel_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    category: Optional[str] = Query(None, description="Filter by certificate category"),
    authorization: Optional[str] = Header(None)
):
    """
    List all certificates for a vessel using PK begins_with pattern.
    Optionally filter by category.
    """
    event = await lambda_to_fastapi_response(
        request, 
        path_params={"vessel_id": vessel_id},
        query_params={"category": category} if category else {}
    )
    result = list_certificates_handler(event, None)
    return parse_lambda_response(result)

@certificate_router.get("/{certificate_id}", summary="Get Certificate")
async def get_certificate_route(
    vessel_id: str,
    certificate_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """
    Get a single certificate by ID.
    """
    event = await lambda_to_fastapi_response(
        request, 
        path_params={
            "vessel_id": vessel_id,
            "certificate_id": certificate_id
        }
    )
    result = get_certificate_handler(event, None)
    return parse_lambda_response(result)

@certificate_router.put("/{certificate_id}", summary="Update Certificate")
async def update_certificate_route(
    vessel_id: str,
    certificate_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """
    Update an existing certificate (admin only).
    Supports multipart/form-data for file uploads.
    """
    event = await lambda_to_fastapi_response(
        request, 
        path_params={
            "vessel_id": vessel_id,
            "certificate_id": certificate_id
        }
    )
    result = update_certificate_handler(event, None)
    return parse_lambda_response(result)

@certificate_router.delete("/{certificate_id}", summary="Delete Certificate")
async def delete_certificate_route(
    vessel_id: str,
    certificate_id: str,
    request: Request,
    tenant_ctx = Depends(require_role("admin")),
    authorization: Optional[str] = Header(None)
):
    """
    Delete a certificate and its associated files from S3 (admin only).
    """
    event = await lambda_to_fastapi_response(
        request, 
        path_params={
            "vessel_id": vessel_id,
            "certificate_id": certificate_id
        }
    )
    result = delete_certificate_handler(event, None)
    return parse_lambda_response(result)

# ============================================================================
# INCLUDE ALL ROUTERS IN MAIN API ROUTER
# ============================================================================
api_router.include_router(inspector_router)
api_router.include_router(admin_admin_router)
api_router.include_router(inspector_me_router)
api_router.include_router(admin_router)
api_router.include_router(admin_profile_router)
api_router.include_router(admin_inspector_router)
api_router.include_router(vessel_router)
api_router.include_router(crew_router)
api_router.include_router(crew_form_router)  # Added missing router
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
api_router.include_router(notifications_router)
api_router.include_router(recurring_inspection_router)
api_router.include_router(system_logs_router)
api_router.include_router(company_notifications_router)
api_router.include_router(certificate_router)
