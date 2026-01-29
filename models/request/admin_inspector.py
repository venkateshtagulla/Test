"""
Admin-side request models for inspector creation and retrieval.
"""
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


'''class AdminCreateInspectorRequest(BaseModel):
    """
    Admin payload to create an inspector (no self-signup flow).

    This model also performs strict validation to ensure that
    DynamoDB secondary index keys (like email) are never empty
    strings, which would cause ValidationException errors.
    """

    first_name: str = Field(..., description="Inspector first name.")
    last_name: str = Field(..., description="Inspector last name.")
    email: EmailStr = Field(..., description="Inspector email address.")
    phone_number: Optional[str] = Field(default=None, description="Optional phone number.")
    password: str = Field(..., description="Initial password to set for the inspector.")
    role: Optional[str] = Field(default=None, description="Role for the inspector.")
    id_proof_url: Optional[str] = Field(default=None, description="S3 URL for ID proof.")
    address_proof_url: Optional[str] = Field(default=None, description="S3 URL for address proof.")
    additional_docs: Optional[List[str]] = Field(
        default=None, description="Optional list of additional document URLs."
    )

    @validator("first_name", "last_name", "password")
    def _non_empty_string(cls, value: str) -> str:
        """
        Ensure required string fields are not empty or only whitespace.
        """

        if value is None:
            raise ValueError("Field is required")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field must not be empty")
        return cleaned

    @validator("email")
    def _clean_email(cls, value: EmailStr) -> EmailStr:
        """
        Normalize and validate email to avoid empty or whitespace-only strings.
        """

        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("Email must not be empty")
        return EmailStr(cleaned)

'''
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

class AdminCreateInspectorRequest(BaseModel):
    first_name: str = Field(..., description="Inspector first name.")
    last_name: str = Field(..., description="Inspector last name.")
    email: EmailStr = Field(..., description="Inspector email address.")
    phone_number: Optional[str] = Field(default=None, description="Optional phone number.")
    password: str = Field(..., description="Initial password to set for the inspector.")
    role: Optional[str] = Field(default=None, description="Role for the inspector.")
    id_proof_url: Optional[str] = Field(default=None, description="S3 URL for ID proof.")
    address_proof_url: Optional[str] = Field(default=None, description="S3 URL for address proof.")
    additional_docs: Optional[List[str]] = Field(
        default=None, description="Optional list of additional document URLs."
    )

    # V2 style field_validator
    @field_validator("first_name", "last_name", "password", mode="before")
    @classmethod
    def _non_empty_string(cls, value: str) -> str:
        if value is None:
            raise ValueError("Field is required")
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field must not be empty")
        return cleaned

    @field_validator("email", mode="before")
    @classmethod
    def _clean_email(cls, value):
        """
        Normalize and validate email. 
        Just return the string; Pydantic's EmailStr type handles the rest.
        """
        if value is None:
            raise ValueError("Email is required")
        cleaned = str(value).strip().lower()
        if not cleaned:
            raise ValueError("Email must not be empty")
        return cleaned # Fixed: Do NOT wrap in EmailStr()
class GetAdminInspectorRequest(BaseModel):
    """
    Request for fetching an inspector by id (admin view).
    """

    inspector_id: str = Field(..., description="Inspector identifier.")


class ListAdminInspectorsRequest(BaseModel):
    """
    Request model for listing inspectors with pagination.
    """

    page: int = Field(1, ge=1, description="Page number (1-based).")
    limit: int = Field(20, ge=1, le=100, description="Number of records per page.")


class AdminResetInspectorPasswordRequest(BaseModel):
    """
    Request model for admin to reset inspector password.
    """

    inspector_id: str = Field(..., description="Inspector identifier.")
    password: str = Field(..., description="New password for the inspector.")

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


class AdminDeleteInspectorRequest(BaseModel):
    """
    Request model for admin to delete (soft delete) an inspector.
    """

    inspector_id: str = Field(..., description="Inspector identifier to delete.")
