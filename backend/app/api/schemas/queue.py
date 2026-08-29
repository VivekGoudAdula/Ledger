"""API Schemas for Queue Transport & Telemetry.

Defines Pydantic models for publishing work items and querying stream metrics.
"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PublishWorkRequest(BaseModel):
    """Request schema for evaluating admission and enqueuing a work item."""

    work_item_id: str = Field(..., description="ID of SignalEvent or CoalescedIncident")
    work_item_type: str = Field(default="signal", description="Type of work item: 'signal' or 'incident'")


class QueueMessageResponse(BaseModel):
    """Response schema representing a QueueMessage payload."""

    message_id: str
    work_item_id: str
    tenant_id: str
    schema_version: int
    effective_value: float
    value_per_compute: float
    admission_decision_id: str
    transport_id: str | None = None
    enqueued_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublishWorkResponse(BaseModel):
    """Response schema for publish work requests."""

    work_item_id: str
    status: str
    decision: str
    message: QueueMessageResponse | None = None


class QueueMetricsResponse(BaseModel):
    """Telemetry response schema for queue depth and consumer statistics."""

    stream_length: int
    pending_count: int
    consumer_count: int
    stream_name: str
    consumer_group: str

    model_config = ConfigDict(from_attributes=True)
