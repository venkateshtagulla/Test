"""
Response models for crew operations.
"""
from typing import List, Optional

from pydantic import BaseModel


class CrewProfile(BaseModel):
    """
    Crew profile representation for /me endpoint.
    """

    crew_id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None


class CrewResponse(BaseModel):
    """
    Serialized crew response.
    """

    crew_id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    id_proof_url: Optional[str] = None
    address_proof_url: Optional[str] = None
    additional_docs: Optional[list] = None


class CrewListResponse(BaseModel):
    """
    Paginated list of crew records.
    """

    crew: List[CrewResponse]
    page: int
    limit: int
    has_next: bool


class AdminDeleteCrewResponse(BaseModel):
    """
    Response for successful crew deletion (soft delete).
    """

    crew_id: str
    deleted: bool
    message: str
