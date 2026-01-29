"""
Database model for Inspector records.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class InspectorDBModel(BaseModel):
    """
    DynamoDB representation of an inspector.
    """

    inspector_id: str = Field(default_factory=lambda: str(uuid4()))
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    password_hash: str
    role: Optional[str] = None
    company_code: Optional[str] = None
    status: str = Field(default="active", description="User status: active or deleted")
    id_proof_url: Optional[str] = None
    address_proof_url: Optional[str] = None
    additional_docs: Optional[list] = Field(default=None, description="Optional list of additional document URLs.")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


    class Config:
        orm_mode = True

