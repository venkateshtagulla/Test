"""
Response models for inspection assignments.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RelatedVessel(BaseModel):
    """
    Minimal vessel information associated with an inspection assignment.
    """

    vessel_id: str
    name: Optional[str] = None
    vessel_type: Optional[str] = None
    imo_number: Optional[str] = None


class RelatedUser(BaseModel):
    """
    Minimal assignee user information (inspector or crew).
    """

    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    user_type: str


class RelatedAdmin(BaseModel):
    """
    Minimal admin information who created the assignment.
    """

    admin_id: str
    name: Optional[str] = None
    email: Optional[str] = None


class RelatedForm(BaseModel):
    """
    Form information associated with an assignment, including questions.
    """

    form_id: str
    title: Optional[str] = None
    status: Optional[str] = Field(
        default=None,
        description="Form status: start (no answers), continue (some answers), completed (all answered).",
    )
    progress_percentage: Optional[float] = Field(
        default=None,
        description="Percentage of questions answered (0-100).",
    )
    due_date: Optional[str] = None
    vessel_id: Optional[str] = None
    description: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of questions with order, prompt, type, options, and answer.",
    )


class InspectionAssignmentResponse(BaseModel):
    """
    Serialized inspection assignment response payload.
    """

    assignment_id: str
    form_id: str
    vessel_id: Optional[str] = None
    created_by_admin_id: str
    assignee_id: str
    assignee_type: str
    role: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    status: str
    inspection_name: Optional[str] = Field(default=None, description="User-provided name for the inspection.")
    inspection_status: Optional[str] = Field(
        default=None,
        description=(
            "Derived form status for this assignment: "
            "pending (no answers), in_progress (some answers), completed (all answered)."
        ),
    )
    inspection_progress_percentage: Optional[float] = Field(
        default=None,
        description="Derived completion percentage for this assignment (0-100).",
    )
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    vessel: Optional[RelatedVessel] = Field(
        default=None,
        description="Expanded vessel information for the assignment.",
    )
    assignee: Optional[RelatedUser] = Field(
        default=None,
        description="Expanded user (inspector or crew) details.",
    )
    admin: Optional[RelatedAdmin] = Field(
        default=None,
        description="Expanded admin details for the creator.",
    )
    forms: List[RelatedForm] = Field(
        default_factory=list,
        description="List of inspection forms associated with this assignment.",
    )


class PaginatedInspectionAssignmentsResponse(BaseModel):
    """
    Paginated inspection assignment listing response.
    """

    items: List[InspectionAssignmentResponse]
    page: int
    limit: int
    has_next: bool = Field(default=False, description="Whether more items are available.")