"""
Response models for admin authentication flows.
"""
from typing import Optional

from pydantic import BaseModel, EmailStr


class AdminTokenPair(BaseModel):
    """
    Access and refresh token bundle for admins.
    """

    access_token: str
    refresh_token: str


class AdminAuthResponse(BaseModel):
    """
    Response schema for admin login/register flows.
    """

    admin_id: str
    email: EmailStr
    tokens: AdminTokenPair


class AdminProfile(BaseModel):
    """
    Admin profile representation.
    """

    admin_id: str
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]



