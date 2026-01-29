"""
Database model for Crew records.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CrewDBModel(BaseModel):
    """
    DynamoDB representation of a crew member.
    """

    crew_id: str = Field(default_factory=lambda: str(uuid4()))
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    password_hash: Optional[str] = None
    role: Optional[str] = None
    company_code: Optional[str] = None
    status: str = Field(default="active", description="User status: active or deleted")
    id_proof_url: Optional[str] = None
    address_proof_url: Optional[str] = None
    additional_docs: Optional[List[str]] = Field(default=None, description="Optional list of additional document URLs.")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


    class Config:
        orm_mode = True

