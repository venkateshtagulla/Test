"""
Database model for Vessel Inspection Form records.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class InspectionFormDBModel(BaseModel):
    """
    DynamoDB representation of an inspection form assigned to a vessel and inspector/crew.
    """

    form_id: str = Field(default_factory=lambda: str(uuid4()))
    vessel_id: str
    created_by_admin_id: str = Field(
        description="Admin who created the form."
    )
    ship_id: Optional[str] = Field(
        default=None,
        description="Optional reference to a ship identifier if needed by upstream systems.",
    )
    title: str
    description: Optional[str] = None
    status: str = Field(
        default="Unassigned",
        description="Form workflow status: Unassigned, In Progress, Closed.",
    )
    assigned_inspector_id: Optional[str] = Field(
        default=None, description="Inspector responsible for this form."
    )
    assigned_crew_id: Optional[str] = Field(
        default=None, description="Crew member responsible for this form, if any."
    )
    due_date: Optional[str] = Field(
        default=None,
        description="ISO8601 date for when this inspection form is due.",
    )
    last_synced_at: Optional[str] = Field(
        default=None,
        description="Client-side last sync timestamp, ISO8601.",
    )
    questions: List[dict] = Field(
        default_factory=list,
        description="Ordered list of question objects with type, prompt, and options.",
    )
    # Recurrence / reminder configuration for this form
    recurrence_start_date: Optional[str] = Field(
        default=None,
        description="Optional ISO8601 date when recurrence of this form starts.",
    )
    recurrence_interval_value: Optional[int] = Field(
        default=None,
        description="How often the form should recur (numeric component).",
    )
    recurrence_interval_unit: Optional[str] = Field(
        default=None,
        description="Unit for recurrence interval: day, week, month, or year.",
    )
    reminder_before_value: Optional[int] = Field(
        default=None,
        description="How many units before due_date to send a reminder.",
    )
    reminder_before_unit: Optional[str] = Field(
        default=None,
        description="Unit for reminder offset: day, week, or month.",
    )
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        orm_mode = True



