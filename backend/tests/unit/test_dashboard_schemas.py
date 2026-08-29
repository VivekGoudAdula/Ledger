"""Unit Tests for Dashboard Presentation Schemas.

Validates DashboardSummaryDTO, WorkerSnapshotDTO, and EventTraceDTO fields.
"""

from app.dashboard.schemas import (
    DashboardSummaryDTO,
    AdmissionBreakdownDTO,
    WorkerSnapshotDTO,
    RecoveryMetricsDTO,
    IdempotencyMetricsDTO,
    SourceHealthDTO,
    EventTraceDTO,
)


def test_valid_dashboard_summary_dto_construction():
    dto = DashboardSummaryDTO(
        system_status="HEALTHY",
        ingress_rate_sec=5.2,
        processing_capacity_sec=100.0,
        total_ingress_count=150,
        admission_breakdown=AdmissionBreakdownDTO(admitted_count=120, deferred_count=20, shed_count=10),
        queue_pending_count=12,
        workers=[WorkerSnapshotDTO(worker_id="worker-1", state="RUNNING", tasks_completed=40)],
        recovery=RecoveryMetricsDTO(pending_count=12, reclaimed_count=2, already_completed_hits=1),
        idempotency=IdempotencyMetricsDTO(checks_count=150, claims_count=120, hits_count=30),
        sources=[SourceHealthDTO(name="GitHub", status="UP", events_received=100)],
        recent_events=[EventTraceDTO(time_str="10:00:00", source="github", event_type="issue_opened", decision="ADMIT", status="COMPLETED")],
    )

    assert dto.system_status == "HEALTHY"
    assert dto.admission_breakdown.admitted_count == 120
    assert dto.workers[0].worker_id == "worker-1"
    assert dto.sources[0].status == "UP"
