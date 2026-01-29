"""
Database model for Defects.
"""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class DefectDBModel(BaseModel):
    """
    DynamoDB representation of a defect raised during inspection.
    """

    defect_id: str = Field(default_factory=lambda: str(uuid4()))
    vessel_id: str = Field(..., description="Vessel ID where the defect was identified.")
    form_id: Optional[str] = Field(
        default=None,
        description="Optional form ID where the defect was raised.",
    )
    assignment_id: Optional[str] = Field(default=None, description="Assignment ID if raised during assignment.")
    title: str = Field(..., min_length=1, max_length=200, description="Defect title.")
    description: Optional[str] = Field(default=None, max_length=1000, description="Detailed defect description.")
    severity: str = Field(default="minor", description="Defect severity: minor, medium, major, critical.")
    priority: str = Field(default="medium", description="Defect priority: low, medium, high, urgent.")
    status: str = Field(default="open", description="Defect status: open, in_progress, resolved, closed, rejected.")
    # Additional context for richer defect reporting
    location_on_ship: Optional[str] = Field(
        default=None,
        description="Location of the defect on the vessel (e.g., Engine Room, Main Deck).",
    )
    equipment_name: Optional[str] = Field(
        default=None,
        description="Equipment or system where the defect was observed (e.g., Lifeboat Motor).",
    )
    raised_by_inspector_id: Optional[str] = Field(default=None, description="Inspector who raised the defect.")
    raised_by_crew_id: Optional[str] = Field(default=None, description="Crew member who raised the defect.")
    assigned_inspector_id: Optional[str] = Field(default=None, description="Inspector assigned to handle the defect.")
    assigned_crew_id: Optional[str] = Field(default=None, description="Crew member assigned to fix the defect.")
    triggered_question_order: Optional[int] = Field(default=None, description="Question order that triggered this defect.")
    triggered_question_text: Optional[str] = Field(default=None, description="Question text that triggered this defect.")
    photos: Optional[List[str]] = Field(default=None, description="List of photo URLs related to the defect.")
    inspector_comments: Optional[List[str]] = Field(default=None, description="Comments from inspector.")
    crew_comments: Optional[List[str]] = Field(default=None, description="Comments from crew.")
    admin_comments: Optional[List[str]] = Field(default=None, description="Comments from admin.")
    task_activities: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="List of activity logs with action and timestamp.",
    )
    due_date: Optional[str] = Field(default=None, description="ISO8601 date/time when the defect should be resolved.")
    # Analysis section (root cause / impact / recurrence / notes / photos)
    analysis_root_cause: Optional[str] = Field(
        default=None,
        description="Root cause identified during defect analysis.",
    )
    analysis_impact_assessment: Optional[str] = Field(
        default=None,
        description="Impact assessment of the defect (e.g., Low, Medium, High).",
    )
    analysis_recurrence_probability: Optional[str] = Field(
        default=None,
        description="Probability of recurrence (e.g., Rare, Possible, Frequent).",
    )
    analysis_notes: Optional[str] = Field(
        default=None,
        description="Additional notes or recommendations from the analysis.",
    )
    analysis_photos: Optional[List[str]] = Field(
        default=None,
        description="Photo URLs attached as part of the defect analysis.",
    )
    analysis_by_inspector_id: Optional[str] = Field(
        default=None,
        description="Inspector who submitted the latest analysis.",
    )
    analysis_by_crew_id: Optional[str] = Field(
        default=None,
        description="Crew member who submitted the latest analysis.",
    )
    analysis_created_at: Optional[str] = Field(
        default=None,
        description="Timestamp when the first analysis was created.",
    )
    analysis_updated_at: Optional[str] = Field(
        default=None,
        description="Timestamp when the analysis was last updated.",
    )
    resolved_at: Optional[str] = Field(default=None, description="ISO8601 timestamp when defect was resolved.")
    closed_at: Optional[str] = Field(default=None, description="ISO8601 timestamp when defect was closed.")
    approved_by_admin_id: Optional[str] = Field(default=None, description="Admin ID who approved the defect resolution.")
    closed_by_admin_id: Optional[str] = Field(default=None, description="Admin ID who closed the defect.")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        orm_mode = True

