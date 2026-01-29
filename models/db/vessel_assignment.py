"""
Database model for Vessel Assignments.
"""
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class VesselAssignmentDBModel(BaseModel):
    """
    DynamoDB representation of a vessel assignment (crew or inspector to vessel).
    """

    assignment_id: str = Field(default_factory=lambda: str(uuid4()))
    vessel_id: str = Field(..., description="Vessel ID.")
    user_id: str = Field(..., description="Crew ID or Inspector ID.")
    user_type: str = Field(..., description="Either 'crew' or 'inspector'.")
    created_by_admin_id: str = Field(..., description="Admin who created the assignment.")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        orm_mode = True

