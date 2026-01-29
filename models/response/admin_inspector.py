"""
Admin-side response models for inspectors.
"""
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class AdminInspectorResponse(BaseModel):
    """
    Serialized inspector data for admin.
    """

    inspector_id: str
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    role: Optional[str] = None
    id_proof_url: Optional[str] = None
    address_proof_url: Optional[str] = None
    additional_docs: Optional[list] = None


class AdminInspectorListResponse(BaseModel):
    """
    Paginated list of inspectors for admin, including signed URLs.
    """

    inspectors: List[AdminInspectorResponse]
    page: int
    limit: int
    has_next: bool


class AdminDeleteInspectorResponse(BaseModel):
    """
    Response for successful inspector deletion (soft delete).
    """

    inspector_id: str
    deleted: bool
    message: str
