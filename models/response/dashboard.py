"""
Response models for dashboard operations.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DashboardSummaryCard(BaseModel):
    """
    Summary card data for dashboard.
    """

    label: str
    value: int
    change_percentage: Optional[float] = Field(default=None, description="Percentage change (positive or negative).")
    trend: Optional[str] = Field(default=None, description="Trend: 'up' or 'down'.")


class RecentActivity(BaseModel):
    """
    Recent activity item for dashboard.
    """

    action: str = Field(..., description="Activity description.")
    timestamp: str = Field(..., description="ISO8601 timestamp.")
    vessel_name: Optional[str] = Field(default=None, description="Vessel name if applicable.")
    user_name: Optional[str] = Field(default=None, description="User name if applicable.")


class DefectSeverityBreakdown(BaseModel):
    """
    Defect severity distribution for dashboard.
    """

    critical: int = Field(default=0, description="Count of critical defects.")
    major: int = Field(default=0, description="Count of major defects.")
    minor: int = Field(default=0, description="Count of minor defects.")
    medium: int = Field(default=0, description="Count of medium defects.")


class VesselSummary(BaseModel):
    """
    Vessel summary data for dashboard table.
    """

    vessel_id: str
    vessel_name: Optional[str] = None
    defects_count: int = Field(default=0, description="Count of defects for this vessel.")
    audits_count: int = Field(default=0, description="Count of completed audits/forms for this vessel.")
    last_updated: Optional[str] = Field(default=None, description="ISO8601 timestamp of last update.")


class DashboardResponse(BaseModel):
    """
    Complete dashboard data response.
    """

    summary_cards: List[DashboardSummaryCard] = Field(..., description="Summary cards (vessels, defects, audits).")
    recent_activities: List[RecentActivity] = Field(..., description="List of recent activities.")
    defect_severity: DefectSeverityBreakdown = Field(..., description="Defect severity breakdown.")
    vessels: List[VesselSummary] = Field(..., description="Vessel summary list with defect and audit counts.")


class AssignedDefectSummary(BaseModel):
    """
    Summary of a defect assigned to inspector/crew for dashboard.
    """

    defect_id: str
    title: str
    location: Optional[str] = Field(default=None, description="Location on ship.")
    assigned_by: Optional[str] = Field(default=None, description="Name of person who assigned the defect.")
    priority: str = Field(..., description="Defect priority: low, medium, high, urgent.")


class InspectorDashboardResponse(BaseModel):
    """
    Dashboard response for inspector.
    """

    task_assigned: int = Field(..., description="Count of tasks assigned.")
    task_completed: int = Field(..., description="Count of tasks completed.")
    pending: int = Field(..., description="Count of pending tasks.")
    due_soon: int = Field(..., description="Count of tasks due soon.")
    defects: List[AssignedDefectSummary] = Field(..., description="List of defects assigned to inspector.")


class CrewDashboardResponse(BaseModel):
    """
    Dashboard response for crew member.
    """

    task_assigned: int = Field(..., description="Count of tasks assigned.")
    task_completed: int = Field(..., description="Count of tasks completed.")
    pending: int = Field(..., description="Count of pending tasks.")
    due_soon: int = Field(..., description="Count of tasks due soon.")
    defects: List[AssignedDefectSummary] = Field(..., description="List of defects assigned to crew member.")

