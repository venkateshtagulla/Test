"""
Request models for inspector authentication flows.
"""
from pydantic import BaseModel, EmailStr, constr


class InspectorRegisterRequest(BaseModel):
    """
    Payload required to register a new inspector.
    """

    first_name: constr(strip_whitespace=True, min_length=1, max_length=128)
    last_name: constr(strip_whitespace=True, min_length=1, max_length=128)
    email: EmailStr
    password: constr(min_length=8, max_length=64)
    confirm_password: constr(min_length=8, max_length=64)
    phone_number: constr(strip_whitespace=True, min_length=7, max_length=20)
    role: constr(strip_whitespace=True, min_length=1, max_length=50)
    company_code: constr(strip_whitespace=True, min_length=1, max_length=50)


class InspectorLoginRequest(BaseModel):
    """
    Payload required to authenticate an inspector.
    """

    email: EmailStr
    password: constr(min_length=8, max_length=64)


class InspectorProfileRequest(BaseModel):
    """
    Payload required to fetch an inspector profile.
    """

    inspector_id: constr(strip_whitespace=True, min_length=1)

