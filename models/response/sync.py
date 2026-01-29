"""
Response models for sync operations.
"""
from typing import Optional

from pydantic import BaseModel, Field


class SyncResponse(BaseModel):
    """
    Response for sync status check.
    """

    pending_uploads: int = Field(
        default=0,
        description="Number of forms waiting to be synced.",
    )
    synced_forms: int = Field(
        default=0,
        description="Total number of forms successfully synced.",
    )
    failed_syncs: int = Field(
        default=0,
        description="Number of failed sync attempts.",
    )
    last_synced_at: Optional[str] = Field(
        default=None,
        description="ISO8601 timestamp of last successful sync.",
    )
    is_online: bool = Field(
        default=True,
        description="Whether the system is online and ready to sync.",
    )

