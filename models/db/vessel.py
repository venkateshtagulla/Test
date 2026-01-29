"""
Database model for Vessel records.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class VesselDBModel(BaseModel):
    """
    DynamoDB representation of a vessel (ship) belonging to an admin.
    """

    vessel_id: str = Field(default_factory=lambda: str(uuid4()))
    admin_id: str = Field(..., description="Admin who owns/manages this vessel.")
    name: str
    vessel_type: str = Field(
        ...,
        description=(
            "Type of vessel, e.g. Bulk Carrier, Tankers, Container Ships, "
            "Liquid/General Cargo, Other."
        ),
    )
    other_vessel_type: Optional[str] = Field(
        default=None,
        description="Custom type name when vessel_type is 'Other'.",
    )
    imo_number: Optional[str] = Field(
        default=None,
        description="IMO number as a string; can contain letters or digits.",
    )
    status: Optional[str] = Field(default="active", description="High-level status.")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        orm_mode = True



