"""
Request models for S3 uploads.
"""
from typing import Optional

from pydantic import BaseModel, Field


class PresignUploadRequest(BaseModel):
    """
    Payload for generating a pre-signed S3 upload URL.
    """

    file_name: str = Field(..., description="Original file name, used to derive the key.")
    content_type: str = Field(..., description="MIME type of the file.")
    folder: Optional[str] = Field(default=None, description="Optional folder/prefix to organize uploads.")

