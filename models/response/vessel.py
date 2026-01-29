"""
Response models for vessel management.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class VesselDefectResponse(BaseModel):
    """
    Defect information for a vessel detail view.
    """

    defect_id: str
    title: str
    description: Optional[str] = None
    severity: str
    priority: str
    status: str
    location_on_ship: Optional[str] = None
    equipment_name: Optional[str] = None
    form_id: Optional[str] = None
    due_date: Optional[str] = None
    photos: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class VesselFormAssignmentResponse(BaseModel):
    """
    Form assignment information for a vessel detail view.
    """

    form_id: str
    title: str
    description: Optional[str] = None
    status: str
    assigned_to: Optional[str] = Field(
        default=None, description="Name of assigned inspector or crew member"
    )
    assigned_to_id: Optional[str] = Field(
        default=None, description="ID of assigned inspector or crew member"
    )
    assigned_to_type: Optional[str] = Field(
        default=None, description="Type of assignee: 'inspector' or 'crew'"
    )
    assigned_date: Optional[str] = Field(
        default=None, description="ISO8601 date when form was assigned"
    )
    due_date: Optional[str] = Field(
        default=None, description="ISO8601 due date for the form"
    )
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class VesselInspectionResponse(BaseModel):
    """
    Inspection assignment information for a vessel detail view.
    """

    assignment_id: str
    inspection_name: str
    form_id: str
    form_title: str
    assignee_type: str
    assignee_name: str
    role: str
    priority: str
    due_date: str
    status: str
    created_at: str


class VesselResponse(BaseModel):
    """
    Representation of a vessel record returned in APIs.
    """

    vessel_id: str
    name: str
    vessel_type: str
    other_vessel_type: Optional[str]
    imo_number: Optional[str]
    status: Optional[str]


class VesselDetailResponse(BaseModel):
    """
    Detailed vessel information including inspections and defects.
    """

    vessel_id: str
    name: str
    vessel_type: str
    other_vessel_type: Optional[str]
    imo_number: Optional[str]
    status: Optional[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    inspections: List[VesselInspectionResponse] = Field(
        default_factory=list, description="List of inspection assignments for this vessel"
    )
    defects: List[VesselDefectResponse] = Field(
        default_factory=list, description="List of defects for this vessel"
    )


class PaginatedVesselsResponse(BaseModel):
    """
    Paginated vessel listing for an admin.
    """

    items: List[VesselResponse]
    page: int = Field(..., description="Current page number.")
    limit: int = Field(..., description="Maximum number of items returned.")
    has_next: bool = Field(
        default=False,
        description="Indicates whether more items are available for subsequent pages.",
    )