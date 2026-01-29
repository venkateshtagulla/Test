"""
Response models for defect operations.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RelatedUserInfo(BaseModel):
    """
    Minimal user information (inspector or crew) for defect responses.
    """

    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    user_type: str


class RelatedVesselInfo(BaseModel):
    """
    Minimal vessel information for defect responses.
    """

    vessel_id: str
    name: Optional[str] = None
    imo_number: Optional[str] = None


class RelatedFormInfo(BaseModel):
    """
    Minimal form information for defect responses.
    """

    form_id: Optional[str] = None
    title: Optional[str] = None


class DefectActivity(BaseModel):
    """
    Activity log entry for defect history.
    """

    action: str = Field(..., description="Activity action description.")
    timestamp: str = Field(..., description="ISO8601 timestamp of the activity.")
    performed_by: Optional[str] = Field(default=None, description="User ID who performed the action.")


class DefectResponse(BaseModel):
    """
    Serialized defect response payload.
    """

    defect_id: str
    vessel_id: str
    form_id: Optional[str] = None
    assignment_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    priority: str
    status: str
    # Additional context
    location_on_ship: Optional[str] = None
    equipment_name: Optional[str] = None
    raised_by_inspector_id: Optional[str] = None
    raised_by_crew_id: Optional[str] = None
    assigned_inspector_id: Optional[str] = None
    assigned_crew_id: Optional[str] = None
    triggered_question_order: Optional[int] = None
    triggered_question_text: Optional[str] = None
    photos: Optional[List[str]] = None
    inspector_comments: Optional[List[str]] = None
    crew_comments: Optional[List[str]] = None
    admin_comments: Optional[List[str]] = None
    task_activities: Optional[List[Dict[str, str]]] = None
    due_date: Optional[str] = None
    # Analysis fields
    analysis_root_cause: Optional[str] = None
    analysis_impact_assessment: Optional[str] = None
    analysis_recurrence_probability: Optional[str] = None
    analysis_notes: Optional[str] = None
    analysis_photos: Optional[List[str]] = None
    analysis_by_inspector_id: Optional[str] = None
    analysis_by_crew_id: Optional[str] = None
    analysis_created_at: Optional[str] = None
    analysis_updated_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    approved_by_admin_id: Optional[str] = None
    closed_by_admin_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Expanded relations
    vessel: Optional[RelatedVesselInfo] = Field(
        default=None,
        description="Expanded vessel information.",
    )
    form: Optional[RelatedFormInfo] = Field(
        default=None,
        description="Expanded form information.",
    )
    raised_by_inspector: Optional[RelatedUserInfo] = Field(
        default=None,
        description="Expanded inspector information who raised the defect.",
    )
    raised_by_crew: Optional[RelatedUserInfo] = Field(
        default=None,
        description="Expanded crew information who raised the defect.",
    )
    assigned_inspector: Optional[RelatedUserInfo] = Field(
        default=None,
        description="Expanded inspector information assigned to handle the defect.",
    )
    assigned_crew: Optional[RelatedUserInfo] = Field(
        default=None,
        description="Expanded crew information assigned to fix the defect.",
    )


class PaginatedDefectsResponse(BaseModel):
    """
    Paginated defect listing response.
    """

    items: List[DefectResponse]
    page: int
    limit: int
    has_next: bool = Field(default=False, description="Whether more items are available.")

