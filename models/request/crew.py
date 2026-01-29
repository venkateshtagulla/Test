"""
Request models for crew creation and retrieval.
"""
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, constr, validator


class CreateCrewRequest(BaseModel):
    """
    Admin payload to create a crew member.
    """

    first_name: str = Field(..., description="Crew first name.")
    last_name: str = Field(..., description="Crew last name.")
    email: Optional[str] = Field(default=None, description="Optional email.")
    phone_number: Optional[str] = Field(default=None, description="Optional phone number.")
    password: Optional[str] = Field(default=None, description="Password for the crew member.")
    role: Optional[str] = Field(default=None, description="Role for the crew member.")
    id_proof_url: Optional[str] = Field(default=None, description="S3 URL for ID proof.")
    address_proof_url: Optional[str] = Field(default=None, description="S3 URL for address proof.")
    additional_docs: Optional[List[str]] = Field(
        default=None, description="Optional list of additional document URLs."
    )

    @validator("password")
    def _validate_password(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate password if provided (must be at least 8 characters).
        """
        if value is not None:
            cleaned = value.strip()
            if cleaned and len(cleaned) < 8:
                raise ValueError("Password must be at least 8 characters long")
            return cleaned if cleaned else None
        return None


class CrewRegisterRequest(BaseModel):
    """
    Payload required to register a new crew member.
    """

    first_name: constr(strip_whitespace=True, min_length=1, max_length=128)
    last_name: constr(strip_whitespace=True, min_length=1, max_length=128)
    email: EmailStr
    password: constr(min_length=8, max_length=64)
    confirm_password: constr(min_length=8, max_length=64)
    phone_number: constr(strip_whitespace=True, min_length=7, max_length=20)
    role: constr(strip_whitespace=True, min_length=1, max_length=50)
    company_code: constr(strip_whitespace=True, min_length=1, max_length=50)


class CrewLoginRequest(BaseModel):
    """
    Payload required to authenticate a crew member.
    """

    email: EmailStr
    password: constr(min_length=8, max_length=64)


class GetCrewRequest(BaseModel):
    """
    Request for fetching a crew member by id.
    """

    crew_id: str = Field(..., description="Crew identifier.")


class ListCrewRequest(BaseModel):
    """
    Request for listing crew with pagination.
    """

    page: int = Field(1, ge=1, description="Page number (1-based).")
    limit: int = Field(20, ge=1, le=100, description="Number of records per page.")


class AdminResetCrewPasswordRequest(BaseModel):
    """
    Request model for admin to reset crew password.
    """

    crew_id: str = Field(..., description="Crew identifier.")
    password: str = Field(..., description="New password for the crew member.")

    @validator("password")
    def _non_empty_password(cls, value: str) -> str:
        """
        Ensure password is not empty or only whitespace.
        """
        if value is None:
            raise ValueError("Password is required")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Password must not be empty")
        if len(cleaned) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return cleaned


class AdminDeleteCrewRequest(BaseModel):
    """
    Request model for admin to delete (soft delete) a crew member.
    """

    crew_id: str = Field(..., description="Crew identifier to delete.")
