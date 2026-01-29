"""
Response models for inspection form operations.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class InspectionQuestionResponse(BaseModel):
    """
    Serialized question or section representation.
    """

    order: int = Field(..., description="Order of the item.")
    type: str = Field(..., description="Item type: mcq, text, image, or section.")
    prompt: Optional[str] = Field(
        default=None, description="Question text (for questions only)."
    )
    title: Optional[str] = Field(
        default=None, description="Section heading text (for sections only)."
    )
    options: Optional[List[str]] = Field(
        default=None, description="Options for MCQ questions."
    )
    answer: Optional[str] = Field(
        default=None,
        description="Recorded answer for this question, if the form has been filled.",
    )
    media_url: Optional[str] = Field(
        default=None,
        description="Optional URL to an image or media asset associated with the question.",
    )
    allow_image_upload: Optional[bool] = Field(
        default=None,
        description="Whether this question allows image uploads as answers.",
    )


class InspectionFormResponse(BaseModel):
    """
    Serialized inspection form response payload.
    """

    form_id: str
    vessel_id: str
    created_by_admin_id: Optional[str] = None
    ship_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    assigned_inspector_id: Optional[str] = None
    assigned_crew_id: Optional[str] = None
    due_date: Optional[str] = None
    # Recurrence / reminder configuration
    recurrence_start_date: Optional[str] = None
    recurrence_interval_value: Optional[int] = None
    recurrence_interval_unit: Optional[str] = None
    reminder_before_value: Optional[int] = None
    reminder_before_unit: Optional[str] = None
    last_synced_at: Optional[str] = None
    questions: List[InspectionQuestionResponse]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    inspection_name: Optional[str] = None  # For inspector forms list


class PaginatedInspectionFormsResponse(BaseModel):
    """
    Paginated inspection form listing response.
    """

    items: List[InspectionFormResponse]
    page: int
    limit: int
    has_next: bool = Field(default=False, description="Whether there are more items available.")

