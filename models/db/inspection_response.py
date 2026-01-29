"""
Database model for Inspection Response records.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InspectionResponseDBModel(BaseModel):
    """
    DynamoDB representation of a response to a single question within an inspection.
    Responses are scoped per inspection (not per form), enabling form reuse.
    """

    inspection_id: str = Field(
        ...,
        description="ID of the inspection (maps to InspectionAssignment.assignment_id)"
    )
    question_id: str = Field(
        ...,
        description="Question identifier (question order number as string)"
    )
    answer_value: str = Field(
        ...,
        description="The actual answer provided by the inspector/crew"
    )
    is_defect: bool = Field(
        default=False,
        description="Whether this answer was marked as a defect"
    )
    media_url: Optional[str] = Field(
        default=None,
        description="S3 URL for image/media answers"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    class Config:
        orm_mode = True
