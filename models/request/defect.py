"""
Request models for defect operations.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError, constr, validator


class ListDefectsRequest(BaseModel):
    """
    Query parameters for paginated defect listing.
    """

    status: Optional[str] = Field(
        default=None,
        description="Filter defects by status: open, in_progress, resolved, closed, rejected.",
    )
    vessel_id: Optional[str] = Field(
        default=None,
        description="Filter defects by vessel ID.",
    )
    page: int = Field(default=1, ge=1, description="Page number (1-based).")
    limit: int = Field(default=20, ge=1, le=100, description="Number of items per page.")

    @validator("status")
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        """
        Ensure status is valid if provided.
        """
        if value is None:
            return None
        allowed = {"open", "in_progress", "resolved", "closed", "rejected"}
        if value.lower() not in allowed:
            raise ValueError(f"Invalid status. Allowed: {allowed}")
        return value.lower()


class CreateDefectRequest(BaseModel):
    """
    Payload for inspectors/crew to create a new defect from the mobile app.
    """

    vessel_id: str = Field(..., description="Vessel ID where the defect was identified.")
    form_id: Optional[str] = Field(
        default=None,
        description="Optional form ID associated with the defect (current inspection form).",
    )
    assignment_id: Optional[str] = Field(
        default=None,
        description="Optional assignment ID if the defect is raised from a specific inspection assignment.",
    )
    title: str = Field(..., min_length=1, max_length=200, description="Short, human-readable defect title.")
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Detailed description of the defect.",
    )
    severity: str = Field(
        default="minor",
        description="Defect severity: minor, medium, major, critical.",
    )
    priority: str = Field(
        default="medium",
        description="Defect priority: low, medium, high, urgent.",
    )
    location_on_ship: Optional[str] = Field(
        default=None,
        description="Location of the defect on the vessel (e.g., Engine Room, Main Deck).",
    )
    equipment_name: Optional[str] = Field(
        default=None,
        description="Equipment or system where the defect was observed.",
    )
    assignee_id: Optional[str] = Field(
        default=None,
        description="Optional user ID (crew or inspector) to assign this defect to.",
    )
    assignee_type: Optional[str] = Field(
        default=None,
        description="Type of assignee when assignee_id is provided: 'crew' or 'inspector'.",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Optional ISO8601 due date for resolving the defect.",
    )
    # Photos are uploaded via multipart/form-data and stored in S3; this field
    # allows passing pre-signed URLs from the client when not using direct upload.
    photos: Optional[List[str]] = Field(
        default=None,
        description="Optional list of already-uploaded photo URLs related to the defect.",
    )

    @validator("severity")
    def validate_severity(cls, value: str) -> str:
        """
        Ensure severity is valid.
        """

        allowed = {"minor", "medium", "major", "critical"}
        if value.lower() not in allowed:
            raise ValueError(f"Invalid severity. Allowed: {allowed}")
        return value.lower()

    @validator("priority")
    def validate_priority(cls, value: str) -> str:
        """
        Ensure priority is valid.
        """

        allowed = "low", "medium", "high", "urgent"
        if value.lower() not in allowed:
            raise ValueError(f"Invalid priority. Allowed: {set(allowed)}")
        return value.lower()

    @validator("assignee_type")
    def validate_assignee_type(cls, value: Optional[str]) -> Optional[str]:
        """
        When provided, assignee_type must be either 'crew' or 'inspector'.
        """

        if value is None:
            return None
        allowed = {"crew", "inspector"}
        if value not in allowed:
            raise ValueError(f"Invalid assignee_type. Allowed: {allowed}")
        return value


class GetDefectRequest(BaseModel):
    """
    Request for fetching a specific defect.
    """

    defect_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Defect identifier.")


class ApproveDefectRequest(BaseModel):
    """
    Request payload for approving a defect resolution.
    """

    defect_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Defect identifier.")
    comment: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional admin comment when approving the defect.",
    )


class CloseDefectRequest(BaseModel):
    """
    Request payload for closing a defect.
    """

    defect_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Defect identifier.")
    comment: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional admin comment when closing the defect.",
    )


class AddDefectCommentRequest(BaseModel):
    """
    Request payload for adding a comment to a defect.
    """

    defect_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Defect identifier.")
    comment: str = Field(..., min_length=1, max_length=500, description="Comment text to add.")


class UpdateDefectRequest(BaseModel):
    """
    Request payload for updating defect fields.
    """

    defect_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Defect identifier.")
    severity: Optional[str] = Field(
        default=None,
        description="Defect severity: minor, medium, major, critical.",
    )
    priority: Optional[str] = Field(
        default=None,
        description="Defect priority: low, medium, high, urgent.",
    )
    status: Optional[str] = Field(
        default=None,
        description="Defect status: open, in_progress, resolved, closed, rejected.",
    )
    assigned_inspector_id: Optional[str] = Field(
        default=None,
        description="Inspector ID assigned to handle the defect.",
    )
    assigned_crew_id: Optional[str] = Field(
        default=None,
        description="Crew member ID assigned to fix the defect.",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="ISO8601 due date for defect resolution.",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Detailed defect description.",
    )

    @validator("severity")
    def validate_severity(cls, value: Optional[str]) -> Optional[str]:
        """
        Ensure severity is valid if provided.
        """
        if value is None:
            return None
        allowed = {"minor", "medium", "major", "critical"}
        if value.lower() not in allowed:
            raise ValueError(f"Invalid severity. Allowed: {allowed}")
        return value.lower()

    @validator("priority")
    def validate_priority(cls, value: Optional[str]) -> Optional[str]:
        """
        Ensure priority is valid if provided.
        """
        if value is None:
            return None
        allowed = {"low", "medium", "high", "urgent"}
        if value.lower() not in allowed:
            raise ValueError(f"Invalid priority. Allowed: {allowed}")
        return value.lower()

    @validator("status")
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        """
        Ensure status is valid if provided.
        """
        if value is None:
            return None
        allowed = {"open", "in_progress", "resolved", "closed", "rejected"}
        if value.lower() not in allowed:
            raise ValueError(f"Invalid status. Allowed: {allowed}")
        return value.lower()


class DefectAnalysisRequest(BaseModel):
    """
    Request payload for adding/updating analysis details for a defect.
    """

    defect_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Defect identifier.")
    root_cause: str = Field(..., min_length=1, max_length=2000, description="Root cause identified for the defect.")
    impact_assessment: Optional[str] = Field(
        default=None,
        description="Impact assessment (e.g., Low, Medium, High).",
    )
    recurrence_probability: Optional[str] = Field(
        default=None,
        description="Probability of recurrence (e.g., Rare, Possible, Frequent).",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Additional notes or recommendations from the analysis.",
    )
    photos: Optional[List[str]] = Field(
        default=None,
        description="Optional list of photo URLs attached as part of the analysis.",
    )

