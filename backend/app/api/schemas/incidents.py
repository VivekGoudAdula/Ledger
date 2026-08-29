"""API Schemas for Incidents and Coalescing Metrics.

Defines Pydantic models for incident query responses and coalescing telemetry.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class CoalescedIncidentResponse(BaseModel):
    """Response schema representing a CoalescedIncident entity."""

    incident_id: str
    tenant_id: str
    coalesce_key: str
    representative_title: str
    source_types: list[str]
    signal_count: int
    coalescing_method: str
    event_ids: list[str]
    first_seen: datetime
    last_seen: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CoalescingMetricsResponse(BaseModel):
    """Telemetry response schema for coalescing performance metrics."""

    tenant_id: str
    signals_received: int
    signals_coalesced: int
    incidents_created: int
    coalescing_ratio: float
    avg_signals_per_incident: float
