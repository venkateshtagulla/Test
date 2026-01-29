"""
Response models for vessel assignment operations.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class VesselAssignmentResponse(BaseModel):
    """
    Serialized vessel assignment response.
    """

    assignment_id: str
    vessel_id: str
    user_id: str
    user_type: str
    user_name: Optional[str] = Field(default=None, description="Name of the assigned user.")
    user_email: Optional[str] = Field(default=None, description="Email of the assigned user.")
    created_by_admin_id: str
    created_at: str
    updated_at: str


class VesselAssignmentsListResponse(BaseModel):
    """
    List of vessel assignments.
    """

    vessel_id: str
    assignments: List[VesselAssignmentResponse] = Field(
        default_factory=list,
        description="List of assignments for this vessel.",
    )

