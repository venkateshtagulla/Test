"""
Request models for vessel management.
"""
from typing import Optional

from pydantic import BaseModel, Field, constr


class CreateVesselRequest(BaseModel):
    """
    Payload required to create a new vessel for an admin.
    """

    name: constr(strip_whitespace=True, min_length=1, max_length=256)
    vessel_type: constr(strip_whitespace=True, min_length=1, max_length=128)
    other_vessel_type: Optional[constr(strip_whitespace=True, max_length=128)] = None
    imo_number: Optional[constr(strip_whitespace=True, max_length=32)] = None


class GetVesselRequest(BaseModel):
    """
    Request model for fetching a single vessel by id.
    """

    vessel_id: str = Field(..., description="Unique identifier of the vessel.")


class ListVesselsRequest(BaseModel):
    """
    Query parameters for paginated vessel listing.
    """

    page: int = Field(default=1, ge=1, description="Page number (1-based).")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page.")



