"""
Request models for admin authentication flows.
"""
from pydantic import BaseModel, EmailStr, constr


class AdminRegisterRequest(BaseModel):
    """
    Payload required to register a new admin.
    """

    email: EmailStr
    password: constr(min_length=8, max_length=64)
    first_name: constr(strip_whitespace=True, min_length=1, max_length=128) | None = None
    last_name: constr(strip_whitespace=True, min_length=1, max_length=128) | None = None


class AdminLoginRequest(BaseModel):
    """
    Payload required to authenticate an admin.
    """

    email: EmailStr
    password: constr(min_length=8, max_length=64)


class AdminProfileRequest(BaseModel):
    """
    Payload required to fetch an admin profile.
    """

    admin_id: constr(strip_whitespace=True, min_length=1)



