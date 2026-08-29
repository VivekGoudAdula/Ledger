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


# ---------------------------------------------------------------------------
# Queue State DTOs — expose real scheduling metadata from the backend
# ---------------------------------------------------------------------------


class QueueItemDTO(BaseModel):
    """One row in the READY or PROCESSING execution queue with full scheduling metadata."""

    position: int = 0
    event_id: str
    tenant_id: str
    source: str
    event_type: str
    severity: str = "info"
    base_value: float = 0.0
    compute_cost: float = 0.0
    value_per_compute: float = 0.0
    waiting_seconds: float = 0.0
    aging_contribution: float = 0.0
    effective_priority: float = 0.0
    deadline_at: str | None = None
    status: str = "QUEUED"
    worker_id: str | None = None
    attempt: int = 1
    created_at: str = ""
    queued_at: str | None = None
    started_at: str | None = None


class DeferredItemDTO(BaseModel):
    """One row in the DEFERRED work queue showing deferral reason."""

    event_id: str
    tenant_id: str
    source: str
    event_type: str
    base_value: float = 0.0
    compute_cost: float = 0.0
    effective_priority: float = 0.0
    waiting_seconds: float = 0.0
    deadline_at: str | None = None
    reason: str = "DEFERRED_CAPACITY_EXHAUSTED"
    admission_reason: str | None = None
    created_at: str = ""


class CompletedItemDTO(BaseModel):
    """One row in the recent completed/failed outcomes table."""

    event_id: str
    tenant_id: str
    source: str
    event_type: str
    status: str  # COMPLETED, FAILED, SHED
    worker_id: str | None = None
    attempt: int = 1
    duration_seconds: float | None = None
    error: str | None = None
    result_summary: str | None = None
    completed_at: str | None = None


class LifecycleStepDTO(BaseModel):
    """One step in the complete per-event signal lifecycle."""

    step: str  # e.g. RECEIVED, NORMALIZED, COALESCED, VALUED, ADMISSION_DECIDED, QUEUED, ...
    status: str  # DONE, SKIPPED, PENDING
    timestamp: str | None = None
    detail: str | None = None


class EventLifecycleDTO(BaseModel):
    """Complete end-to-end lifecycle for a single event, sourced from real DB records."""

    event_id: str
    tenant_id: str
    source: str
    event_type: str
    severity: str
    current_status: str
    lifecycle_steps: list[LifecycleStepDTO] = Field(default_factory=list)
    # Valuation details
    base_value: float | None = None
    compute_cost: float | None = None
    value_per_compute: float | None = None
    urgency: float | None = None
    confidence: float | None = None
    consequence_of_drop: float | None = None
    # Admission details
    admission_decision: str | None = None
    admission_reason: str | None = None
    # Coalescing details
    coalesced_into_id: str | None = None
    coalesced_count: int = 1
    # Worker execution details
    worker_id: str | None = None
    attempt_number: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    error: str | None = None
    # Idempotency details
    idempotency_hit: bool = False
    idempotency_status: str | None = None


class QueueStateDTO(BaseModel):
    """Full execution queue state snapshot from backend. Frontend renders, backend orders."""

    ready_queue: list[QueueItemDTO] = Field(default_factory=list)
    processing_now: list[QueueItemDTO] = Field(default_factory=list)
    deferred_queue: list[DeferredItemDTO] = Field(default_factory=list)
    completed_recent: list[CompletedItemDTO] = Field(default_factory=list)
    failed_recent: list[CompletedItemDTO] = Field(default_factory=list)
    shed_recent: list[CompletedItemDTO] = Field(default_factory=list)
    total_ready: int = 0
    total_processing: int = 0
    total_deferred: int = 0
    snapshot_at: str = ""
