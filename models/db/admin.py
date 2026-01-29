"""
Database model for Admin records.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


class AdminDBModel(BaseModel):
    """
    DynamoDB representation of an admin user.
    """

    admin_id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    password_hash: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        orm_mode = True



