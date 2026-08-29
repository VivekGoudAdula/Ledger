"""API Schemas for Event Ingestion.

Defines Pydantic models for HTTP request validation and API responses.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class IngestSignalRequest(BaseModel):
    """Payload format for direct API signal ingestion."""

    tenant_id: str = Field(default="default", description="Tenant identifier")
    payload: dict[str, Any] = Field(..., description="Raw signal payload dictionary")


class SignalEventResponse(BaseModel):
    """Response schema representing a canonical SignalEvent."""

    event_id: str
    source_type: str
    source_id: str
    tenant_id: str
    event_type: str
    severity: str
    payload_hash: str
    coalesce_key: str
    status: str
    is_duplicate: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    deadline_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class IngestionErrorResponse(BaseModel):
    """Structured error response format."""

    error: str
    message: str
    details: dict[str, Any] | None = None
