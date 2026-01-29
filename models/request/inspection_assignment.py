"""
Request models for inspection assignments.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class CreateInspectionAssignmentRequest(BaseModel):
    """
    Payload to create an inspection assignment.
    """

    form_id: str = Field(..., description="Inspection form identifier.")
    vessel_id: Optional[str] = Field(
        default=None, description="Optional vessel identifier linked to the assignment."
    )
    assignee_id: str = Field(
        ..., description="User id of the crew or inspector."
    )
    assignee_type: str = Field(
        ..., description="Either 'crew' or 'inspector'."
    )
    role: Optional[str] = Field(default=None, description="Role for the assignee.")
    priority: Optional[str] = Field(default=None, description="Priority label.")
    due_date: Optional[str] = Field(default=None, description="Optional ISO8601 due date.")
    inspection_name: Optional[str] = Field(default=None, description="Optional user-provided name for the inspection.")
    assignment_id: Optional[str] = Field(
        default=None,
        description="Optional existing assignment ID to add this form to. If provided, the form will be added to the existing assignment instead of creating a new one."
    )

    @validator("assignee_type")
    def validate_assignee_type(cls, value: str) -> str:
        """
        Ensure assignee type is either crew or inspector.
        """

        allowed = {"crew", "inspector"}
        if value not in allowed:
            raise ValueError(f"Invalid assignee_type. Allowed: {allowed}")
        return value


class GetInspectionAssignmentRequest(BaseModel):
    """
    Request for fetching a specific inspection assignment.
    """

    assignment_id: str = Field(..., description="Assignment identifier.")


class ListInspectionAssignmentsRequest(BaseModel):
    """
    Query parameters for paginated inspection assignment listing.
    """

    form_id: Optional[str] = Field(
        default=None, description="Optional filter by form id."
    )
    page: int = Field(default=1, ge=1, description="Page number (1-based).")
    limit: int = Field(default=20, ge=1, le=100, description="Number of items per page.")
    search: Optional[str] = Field(default=None, description="Optional search term to filter by form title or vessel name.")


class BulkCreateInspectionAssignmentRequest(BaseModel):
    """
    Payload to create multiple inspection assignments to inspectors.
    """

    assignee_id: str = Field(..., description="Inspector ID to assign forms to.")
    form_ids: List[str] = Field(..., min_items=1, description="List of form IDs to assign.")
    vessel_id: Optional[str] = Field(
        default=None, description="Optional vessel identifier linked to all assignments."
    )
    role: Optional[str] = Field(default=None, description="Role for the assignee.")
    priority: Optional[str] = Field(default=None, description="Priority label.")
    due_date: Optional[str] = Field(default=None, description="Optional ISO8601 due date.")
    inspection_name: Optional[str] = Field(default=None, description="Optional user-provided name for the inspection.")


class CreateCrewInspectionAssignmentRequest(BaseModel):
    """
    Payload to create a single inspection assignment to a crew member.
    """

    form_id: str = Field(..., description="Inspection form identifier.")
    crew_id: str = Field(..., description="Crew member ID.")
    vessel_id: Optional[str] = Field(
        default=None, description="Optional vessel identifier linked to the assignment."
    )
    role: Optional[str] = Field(default=None, description="Role for the assignee.")
    priority: Optional[str] = Field(default=None, description="Priority label.")
    due_date: Optional[str] = Field(default=None, description="Optional ISO8601 due date.")
    inspection_name: Optional[str] = Field(default=None, description="Optional user-provided name for the inspection.")


class DeleteInspectionAssignmentRequest(BaseModel):
    """
    Request for deleting an inspection assignment by form_id.
    """

    form_id: str = Field(..., description="Form identifier to remove from assignment.")

