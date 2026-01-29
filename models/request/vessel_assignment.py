"""
Request models for vessel assignment operations.
"""
from pydantic import BaseModel, Field, validator


class CreateVesselAssignmentRequest(BaseModel):
    """
    Payload to assign a crew member or inspector to a vessel.
    """

    vessel_id: str = Field(..., description="Vessel ID to assign to.")
    user_id: str = Field(..., description="Crew ID or Inspector ID to assign.")
    user_type: str = Field(..., description="Either 'crew' or 'inspector'.")

    @validator("user_type")
    def validate_user_type(cls, value: str) -> str:
        """
        Ensure user_type is either crew or inspector.
        """

        allowed = {"crew", "inspector"}
        if value not in allowed:
            raise ValueError(f"Invalid user_type. Allowed: {allowed}")
        return value


class GetVesselAssignmentsRequest(BaseModel):
    """
    Request to get vessel assignments.
    Can filter by vessel_id, user_id, or user_type.
    """

    vessel_id: str = Field(..., description="Vessel ID to get assignments for.")

