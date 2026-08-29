"""Dashboard Presentation DTO Schemas.

Defines frontend-friendly Pydantic data transfer models for REST snapshots and WebSocket streaming.
"""

from typing import Any
from pydantic import BaseModel, Field


class AdmissionBreakdownDTO(BaseModel):
    """Counts of admitted, deferred, and shed decisions."""

    admitted_count: int = 0
    deferred_count: int = 0
    shed_count: int = 0


class WorkerSnapshotDTO(BaseModel):
    """Telemetry snapshot for an individual worker process."""

    worker_id: str
    state: str
    current_task: str | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0


class RecoveryMetricsDTO(BaseModel):
    """Failure recovery telemetry snapshot."""

    pending_count: int = 0
    stale_count: int = 0
    reclaimed_count: int = 0
    already_completed_hits: int = 0
    failures_count: int = 0


class IdempotencyMetricsDTO(BaseModel):
    """Database-enforced idempotency metrics snapshot."""

    checks_count: int = 0
    claims_count: int = 0
    hits_count: int = 0
    duplicates_prevented_count: int = 0


class SourceHealthDTO(BaseModel):
    """Health and ingress metrics snapshot for a signal source."""

    name: str
    status: str
    events_received: int = 0
    last_poll_time: str = "N/A"


class EventTraceDTO(BaseModel):
    """Recent event trace row for dashboard table presentation."""

    event_id: str | None = None
    time_str: str
    source: str
    event_type: str
    tenant_id: str = "tenant_default"
    worker_id: str = "worker-1"
    expected_value: float | None = None
    compute_cost: float | None = None
    urgency: float | None = None
    confidence: float | None = None
    consequence_of_drop: float | None = None
    admission_reason: str | None = None
    decision: str = "ADMIT"
    status: str = "QUEUED"


class DashboardSummaryDTO(BaseModel):
    """Complete authoritative live dashboard state snapshot DTO."""

    system_status: str = "HEALTHY"
    uptime_seconds: float = 0.0
    ingress_rate_sec: float = 0.0
    processing_capacity_sec: float = 100.0
    total_ingress_count: int = 0
    admission_breakdown: AdmissionBreakdownDTO = Field(default_factory=AdmissionBreakdownDTO)
    queue_pending_count: int = 0
    workers: list[WorkerSnapshotDTO] = Field(default_factory=list)
    recovery: RecoveryMetricsDTO = Field(default_factory=RecoveryMetricsDTO)
    idempotency: IdempotencyMetricsDTO = Field(default_factory=IdempotencyMetricsDTO)
    sources: list[SourceHealthDTO] = Field(default_factory=list)
    recent_events: list[EventTraceDTO] = Field(default_factory=list)
