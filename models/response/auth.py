"""
Response models for inspector authentication flows.
"""
from typing import Optional

from pydantic import BaseModel, EmailStr


class TokenPair(BaseModel):
    """
    Access and refresh token bundle.
    """

    access_token: str
    refresh_token: str


class AuthResponse(BaseModel):
    """
    Response schema for login/register flows.
    """

    inspector_id: str
    email: EmailStr
    tokens: TokenPair


class CrewAuthResponse(BaseModel):
    """
    Response schema for crew login/register flows.
    """

    crew_id: str
    email: EmailStr
    tokens: TokenPair


class InspectorProfile(BaseModel):
    """
    Inspector profile representation.
    """

    inspector_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str]

