"""
Database model for Inspection Assignments.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class InspectionAssignmentDBModel(BaseModel):
    """
    DynamoDB representation of an inspection assignment linking a form to a vessel and assignee.
    """

    assignment_id: str = Field(default_factory=lambda: str(uuid4()))
    form_id: str
    vessel_id: Optional[str] = Field(default=None, description="Optional vessel linked to the assignment.")
    created_by_admin_id: str = Field(..., description="Admin who created the assignment.")
    assignee_id: str = Field(..., description="Crew or inspector user id.")
    assignee_type: str = Field(..., description="Either 'crew' or 'inspector'.")
    role: Optional[str] = Field(default=None, description="Role assigned for the inspection.")
    priority: Optional[str] = Field(default=None, description="Priority label such as low, medium, high.")
    due_date: Optional[str] = Field(default=None, description="Optional ISO8601 due date for the assignment.")
    status: str = Field(default="assigned", description="Assignment status.")
    inspection_name: Optional[str] = Field(default=None, description="Optional user-provided name for the inspection.")
    parent_assignment_id: Optional[str] = Field(
        default=None,
        description="Optional parent assignment ID to group multiple forms under the same assignment."
    )
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        orm_mode = True

