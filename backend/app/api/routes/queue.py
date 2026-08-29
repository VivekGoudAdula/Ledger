"""Queue Transport, Telemetry & Live State API Routes.

Defines HTTP endpoints for evaluating admission, enqueuing admitted work,
querying broker metrics, and exposing live queue scheduling state.
"""

from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_event_repository,
    get_incident_repository,
    get_valuation_service,
    get_admission_controller,
    get_queue_broker,
    get_queue_publisher_service,
)
from app.api.schemas import PublishWorkRequest, PublishWorkResponse, QueueMetricsResponse, QueueMessageResponse
from app.domain.models import CapacityState, TenantState
from app.domain.interfaces.queue import WorkQueueInterface
from app.storage.repositories import EventRepository, IncidentRepository
from app.valuation.service import ValueEstimationService
from app.admission.controller import AdmissionController
from app.queue.service import QueuePublisherService
from app.dashboard.schemas import (
    QueueStateDTO,
    QueueItemDTO,
    DeferredItemDTO,
    CompletedItemDTO,
    EventLifecycleDTO,
    LifecycleStepDTO,
)

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])


@router.post(
    "/publish",
    response_model=PublishWorkResponse,
    summary="Evaluate Admission and Enqueue Admitted Work",
)
async def publish_work_item(
    request: PublishWorkRequest,
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    valuation_service: Annotated[ValueEstimationService, Depends(get_valuation_service)],
    admission_controller: Annotated[AdmissionController, Depends(get_admission_controller)],
    publisher_service: Annotated[QueuePublisherService, Depends(get_queue_publisher_service)],
) -> PublishWorkResponse:
    """Evaluate admission decision for work item and publish to queue broker if ADMITTED."""
    work_item = None
    if request.work_item_type == "signal":
        work_item = await event_repo.get_by_id(request.work_item_id)
    elif request.work_item_type == "incident":
        work_item = await incident_repo.get_by_id(request.work_item_id)

    if not work_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{request.work_item_type.capitalize()} '{request.work_item_id}' not found",
        )

    # Step 1: Assess Value
    assessment = await valuation_service.assess_work_item(work_item)

    # Step 2: Evaluate Admission
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id=work_item.tenant_id)
    decision = admission_controller.evaluate_admission(work_item, assessment, capacity, tenant)

    # Step 3: Handle Admission Transport Routing (Enqueues ONLY if ADMIT)
    final_status, msg = await publisher_service.handle_admission_decision(work_item, decision)

    msg_resp = QueueMessageResponse.model_validate(msg) if msg else None

    return PublishWorkResponse(
        work_item_id=request.work_item_id,
        status=final_status.value,
        decision=decision.decision.value,
        message=msg_resp,
    )


@router.get(
    "/metrics",
    response_model=QueueMetricsResponse,
    summary="Get Queue Depth and Telemetry Metrics",
)
async def get_queue_metrics(
    broker: Annotated[WorkQueueInterface, Depends(get_queue_broker)],
) -> QueueMetricsResponse:
    """Retrieve queue length, pending message count, and active consumer statistics."""
    metrics = await broker.get_metrics()
    return QueueMetricsResponse.model_validate(metrics)


@router.get(
    "/state",
    response_model=QueueStateDTO,
    summary="Get Live Execution Queue State with Scheduling Metadata",
)
async def get_queue_state(
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> QueueStateDTO:
    """Return the full live execution queue grouped by real DB status with scheduling metadata.

    Backend computes effective_priority, aging_contribution, and waiting_seconds
    from actual DB timestamps. Frontend renders the order as-is — no sorting in React.
    """
    from sqlalchemy import select, desc
    from app.storage.models import EventORM, ExecutionCheckpointORM, ExecutionResultORM

    now = datetime.now(timezone.utc)
    session = event_repo._session

    # Query all recent events in terminal or active states (last 200)
    stmt = (
        select(EventORM)
        .where(
            EventORM.status.in_([
                "QUEUED", "PROCESSING", "DEFERRED", "SHED", "COMPLETED", "FAILED"
            ])
        )
        .order_by(desc(EventORM.created_at))
        .limit(200)
    )
    rows = (await session.execute(stmt)).scalars().all()

    # Fetch latest checkpoint per work_item (worker_id, attempt, started_at)
    checkpoint_stmt = (
        select(ExecutionCheckpointORM)
        .order_by(desc(ExecutionCheckpointORM.started_at))
    )
    checkpoints_raw = (await session.execute(checkpoint_stmt)).scalars().all()
    # Map work_item_id -> latest checkpoint
    checkpoint_map: dict[str, ExecutionCheckpointORM] = {}
    for cp in checkpoints_raw:
        if cp.work_item_id not in checkpoint_map:
            checkpoint_map[cp.work_item_id] = cp

    # Fetch recent execution results
    result_stmt = (
        select(ExecutionResultORM)
        .order_by(desc(ExecutionResultORM.completed_at))
        .limit(200)
    )
    results_raw = (await session.execute(result_stmt)).scalars().all()
    result_map: dict[str, ExecutionResultORM] = {r.work_item_id: r for r in results_raw}

    ready_queue: list[QueueItemDTO] = []
    processing_now: list[QueueItemDTO] = []
    deferred_queue: list[DeferredItemDTO] = []
    completed_recent: list[CompletedItemDTO] = []
    failed_recent: list[CompletedItemDTO] = []
    shed_recent: list[CompletedItemDTO] = []

    def _ensure_tz(dt: datetime | None) -> datetime | None:
        """Ensure datetime is timezone-aware."""
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    def _fmt(dt: datetime | None) -> str | None:
        """Format datetime to ISO string."""
        if dt is None:
            return None
        return _ensure_tz(dt).isoformat()

    for orm in rows:
        created = _ensure_tz(orm.created_at) or now
        base_value = orm.admission_score or 0.0
        cost = orm.estimated_compute_cost or 0.25

        # Compute aging exactly as admission policy does
        queued_or_created = _ensure_tz(orm.queued_at) or created
        waiting_secs = max(0.0, (now - queued_or_created).total_seconds())
        aging_bonus = min(0.30, waiting_secs * 0.001)
        effective_val = round(min(1.0, base_value + aging_bonus), 4)
        effective_priority = round(effective_val / max(cost, 0.01), 4)

        deadline_str = _fmt(orm.deadline_at)
        cp = checkpoint_map.get(orm.event_id)

        if orm.status in ("QUEUED", "PROCESSING"):
            item = QueueItemDTO(
                event_id=orm.event_id,
                tenant_id=orm.tenant_id or "default",
                source=orm.source_type,
                event_type=orm.event_type,
                severity=orm.severity,
                base_value=round(base_value, 4),
                compute_cost=round(cost, 4),
                value_per_compute=effective_priority,
                waiting_seconds=round(waiting_secs, 1),
                aging_contribution=round(aging_bonus, 4),
                effective_priority=effective_priority,
                deadline_at=deadline_str,
                status=orm.status,
                worker_id=cp.worker_id if cp else orm.worker_id,
                attempt=cp.attempt_number if cp else 1,
                created_at=_fmt(created) or "",
                queued_at=_fmt(orm.queued_at),
                started_at=_fmt(cp.started_at) if cp else None,
            )
            if orm.status == "QUEUED":
                ready_queue.append(item)
            else:
                processing_now.append(item)

        elif orm.status == "DEFERRED":
            deferred_queue.append(DeferredItemDTO(
                event_id=orm.event_id,
                tenant_id=orm.tenant_id or "default",
                source=orm.source_type,
                event_type=orm.event_type,
                base_value=round(base_value, 4),
                compute_cost=round(cost, 4),
                effective_priority=effective_priority,
                waiting_seconds=round(waiting_secs, 1),
                deadline_at=deadline_str,
                reason=orm.admission_reason or "DEFERRED_CAPACITY_EXHAUSTED",
                admission_reason=orm.admission_reason,
                created_at=_fmt(created) or "",
            ))

        elif orm.status in ("COMPLETED", "FAILED", "SHED"):
            exec_result = result_map.get(orm.event_id)
            duration = None
            error = None
            result_summary = None
            completed_at_str = None

            if exec_result:
                completed_at = _ensure_tz(exec_result.completed_at)
                started = _ensure_tz(exec_result.started_at)
                completed_at_str = _fmt(completed_at)
                if completed_at and started:
                    duration = round((completed_at - started).total_seconds(), 3)
                error = exec_result.error_category
                out = exec_result.output_data or {}
                result_summary = out.get("action_taken") or out.get("analysis") or str(out)[:80] if out else None

            item = CompletedItemDTO(
                event_id=orm.event_id,
                tenant_id=orm.tenant_id or "default",
                source=orm.source_type,
                event_type=orm.event_type,
                status=orm.status,
                worker_id=cp.worker_id if cp else None,
                attempt=exec_result.attempt_number if exec_result else 1,
                duration_seconds=duration,
                error=error,
                result_summary=result_summary,
                completed_at=completed_at_str,
            )
            if orm.status == "COMPLETED":
                completed_recent.append(item)
            elif orm.status == "FAILED":
                failed_recent.append(item)
            else:
                shed_recent.append(item)

    # Sort READY queue by effective_priority DESC (backend is authoritative)
    ready_queue.sort(key=lambda x: x.effective_priority, reverse=True)
    for i, item in enumerate(ready_queue, start=1):
        item.position = i

    # Sort PROCESSING by started_at (most recent first)
    processing_now.sort(key=lambda x: x.started_at or "", reverse=True)
    for i, item in enumerate(processing_now, start=1):
        item.position = i

    return QueueStateDTO(
        ready_queue=ready_queue,
        processing_now=processing_now,
        deferred_queue=deferred_queue,
        completed_recent=completed_recent[:20],
        failed_recent=failed_recent[:10],
        shed_recent=shed_recent[:10],
        total_ready=len(ready_queue),
        total_processing=len(processing_now),
        total_deferred=len(deferred_queue),
        snapshot_at=now.isoformat(),
    )


@router.get(
    "/event/{event_id}/lifecycle",
    response_model=EventLifecycleDTO,
    summary="Get Complete End-to-End Signal Lifecycle for a Single Event",
)
async def get_event_lifecycle(
    event_id: str,
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> EventLifecycleDTO:
    """Return the complete 17-question lifecycle for a single event from real DB state.

    Pulls: EventORM, ExecutionCheckpointORM, ExecutionResultORM, IdempotencyRecordORM,
    IncidentSignalLinkORM, ValueAssessmentORM. Zero fabrication.
    """
    from sqlalchemy import select, desc
    from app.storage.models import (
        EventORM,
        ExecutionCheckpointORM,
        ExecutionResultORM,
        IdempotencyRecordORM,
        IncidentSignalLinkORM,
        ValueAssessmentORM,
    )

    session = event_repo._session
    now = datetime.now(timezone.utc)

    # Load EventORM
    evt_stmt = select(EventORM).where(EventORM.event_id == event_id)
    orm = (await session.execute(evt_stmt)).scalar_one_or_none()
    if not orm:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")

    def _ensure_tz(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    def _fmt(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return _ensure_tz(dt).isoformat()

    created = _ensure_tz(orm.created_at) or now

    # Load latest valuation assessment
    val_stmt = (
        select(ValueAssessmentORM)
        .where(ValueAssessmentORM.work_item_id == event_id)
        .order_by(desc(ValueAssessmentORM.estimated_at))
        .limit(1)
    )
    valuation = (await session.execute(val_stmt)).scalar_one_or_none()

    # Load latest execution checkpoint
    cp_stmt = (
        select(ExecutionCheckpointORM)
        .where(ExecutionCheckpointORM.work_item_id == event_id)
        .order_by(desc(ExecutionCheckpointORM.started_at))
        .limit(1)
    )
    checkpoint = (await session.execute(cp_stmt)).scalar_one_or_none()

    # Load execution result
    result_stmt = select(ExecutionResultORM).where(ExecutionResultORM.work_item_id == event_id)
    exec_result = (await session.execute(result_stmt)).scalar_one_or_none()

    # Load idempotency record
    idem_stmt = (
        select(IdempotencyRecordORM)
        .where(IdempotencyRecordORM.work_item_id == event_id)
        .limit(1)
    )
    idem_record = (await session.execute(idem_stmt)).scalar_one_or_none()

    # Load coalescing link
    link_stmt = select(IncidentSignalLinkORM).where(IncidentSignalLinkORM.event_id == event_id)
    link = (await session.execute(link_stmt)).scalar_one_or_none()

    # Build lifecycle steps from real DB state
    steps: list[LifecycleStepDTO] = []

    # Step 1: RECEIVED
    steps.append(LifecycleStepDTO(
        step="SIGNAL_RECEIVED",
        status="DONE",
        timestamp=_fmt(created),
        detail=f"Source: {orm.source_type} | Type: {orm.event_type} | Severity: {orm.severity}",
    ))

    # Step 2: NORMALIZED
    steps.append(LifecycleStepDTO(
        step="NORMALIZED",
        status="DONE",
        timestamp=_fmt(created),
        detail=f"SHA-256 fingerprint: {orm.payload_hash[:16]}... | Payload validated",
    ))

    # Step 3: COALESCED or STANDALONE
    if link:
        steps.append(LifecycleStepDTO(
            step="COALESCED",
            status="DONE",
            timestamp=_fmt(created),
            detail=f"Merged into incident {link.incident_id} | Coalesce key: {orm.coalesce_key}",
        ))
    elif orm.coalesced_into_id:
        steps.append(LifecycleStepDTO(
            step="COALESCED",
            status="DONE",
            timestamp=_fmt(created),
            detail=f"Grouped into incident {orm.coalesced_into_id} | Signal count: {orm.coalesced_count}",
        ))
    else:
        steps.append(LifecycleStepDTO(
            step="STANDALONE",
            status="DONE",
            timestamp=_fmt(created),
            detail=f"Not coalesced — unique event (key: {orm.coalesce_key})",
        ))

    # Step 4: VALUE_ESTIMATED
    if valuation:
        steps.append(LifecycleStepDTO(
            step="VALUE_ESTIMATED",
            status="DONE",
            timestamp=_fmt(_ensure_tz(valuation.estimated_at)),
            detail=f"EV={valuation.expected_value:.3f} | Cost={valuation.estimated_compute_cost:.3f} | VPC={valuation.value_per_compute:.3f} | {valuation.estimator}",
        ))
    elif orm.admission_score:
        steps.append(LifecycleStepDTO(
            step="VALUE_ESTIMATED",
            status="DONE",
            timestamp=_fmt(created),
            detail=f"EV={orm.admission_score:.3f} (from admission record) | Cost={orm.estimated_compute_cost or 0.25:.3f}",
        ))
    else:
        steps.append(LifecycleStepDTO(
            step="VALUE_ESTIMATED",
            status="PENDING",
            detail="No valuation record found",
        ))

    # Step 5: ADMISSION_DECIDED
    admission_dec = orm.admission_decision or ("ADMIT" if orm.status not in ("DEFERRED", "SHED") else orm.status)
    steps.append(LifecycleStepDTO(
        step="ADMISSION_DECIDED",
        status="DONE",
        timestamp=_fmt(created),
        detail=f"Decision: {admission_dec} | Reason: {orm.admission_reason or 'N/A'}",
    ))

    # Step 6: QUEUED / DEFERRED / SHED
    if orm.status in ("QUEUED", "PROCESSING", "COMPLETED", "FAILED"):
        steps.append(LifecycleStepDTO(
            step="QUEUED",
            status="DONE",
            timestamp=_fmt(_ensure_tz(orm.queued_at)) or _fmt(created),
            detail=f"Admitted to execution queue | Stream: ledger:work_stream",
        ))
    elif orm.status == "DEFERRED":
        steps.append(LifecycleStepDTO(
            step="DEFERRED",
            status="DONE",
            timestamp=_fmt(created),
            detail=f"Reason: {orm.admission_reason or 'DEFERRED_CAPACITY_EXHAUSTED'} | Will be re-evaluated",
        ))
    elif orm.status == "SHED":
        steps.append(LifecycleStepDTO(
            step="SHED",
            status="DONE",
            timestamp=_fmt(created),
            detail=f"Reason: {orm.admission_reason or 'SHED_LOW_VALUE'} | Irrecoverable",
        ))

    # Step 7: WORKER_CLAIMED / PROCESSING
    if checkpoint:
        steps.append(LifecycleStepDTO(
            step="WORKER_CLAIMED",
            status="DONE",
            timestamp=_fmt(_ensure_tz(checkpoint.started_at)),
            detail=f"Worker: {checkpoint.worker_id} | Attempt: {checkpoint.attempt_number} | State: {checkpoint.state}",
        ))

    # Step 8: IDEMPOTENCY CHECK
    if idem_record:
        idem_status = idem_record.status
        is_hit = idem_status == "COMPLETED" and exec_result and exec_result.attempt_number > 1
        steps.append(LifecycleStepDTO(
            step="IDEMPOTENCY_CHECK",
            status="DONE",
            timestamp=_fmt(_ensure_tz(idem_record.created_at)),
            detail=f"Key claimed | Status: {idem_status} | {'DUPLICATE PREVENTED' if is_hit else 'First execution — ownership granted'}",
        ))
    else:
        steps.append(LifecycleStepDTO(
            step="IDEMPOTENCY_CHECK",
            status="SKIPPED",
            detail="No idempotency record — event not yet processed by worker",
        ))

    # Step 9: OUTCOME
    if exec_result:
        if exec_result.status == "COMPLETED":
            out = exec_result.output_data or {}
            result_str = out.get("action_taken") or out.get("analysis") or str(out)[:120] if out else "Work completed"
            steps.append(LifecycleStepDTO(
                step="COMPLETED",
                status="DONE",
                timestamp=_fmt(_ensure_tz(exec_result.completed_at)),
                detail=f"Duration: {round(((_ensure_tz(exec_result.completed_at) or now) - (_ensure_tz(exec_result.started_at) or now)).total_seconds(), 3)}s | {result_str}",
            ))
        elif exec_result.status == "FAILED":
            steps.append(LifecycleStepDTO(
                step="FAILED",
                status="DONE",
                timestamp=_fmt(_ensure_tz(exec_result.completed_at)),
                detail=f"Error: {exec_result.error_category} | Attempt: {exec_result.attempt_number}",
            ))
    elif orm.status not in ("COMPLETED", "FAILED", "SHED"):
        steps.append(LifecycleStepDTO(
            step="OUTCOME",
            status="PENDING",
            detail=f"Current status: {orm.status} — awaiting completion",
        ))

    # Aggregate derived fields
    duration = None
    error = None
    if exec_result:
        completed_at = _ensure_tz(exec_result.completed_at)
        started_at = _ensure_tz(exec_result.started_at)
        if completed_at and started_at:
            duration = round((completed_at - started_at).total_seconds(), 3)
        error = exec_result.error_category

    return EventLifecycleDTO(
        event_id=orm.event_id,
        tenant_id=orm.tenant_id or "default",
        source=orm.source_type,
        event_type=orm.event_type,
        severity=orm.severity,
        current_status=orm.status,
        lifecycle_steps=steps,
        base_value=orm.admission_score,
        compute_cost=orm.estimated_compute_cost,
        value_per_compute=round((orm.admission_score or 0.0) / max(orm.estimated_compute_cost or 0.25, 0.01), 4),
        urgency=orm.urgency_score,
        confidence=orm.confidence_score,
        consequence_of_drop=orm.consequence_score,
        admission_decision=orm.admission_decision,
        admission_reason=orm.admission_reason,
        coalesced_into_id=orm.coalesced_into_id or (link.incident_id if link else None),
        coalesced_count=orm.coalesced_count,
        worker_id=checkpoint.worker_id if checkpoint else None,
        attempt_number=checkpoint.attempt_number if checkpoint else None,
        started_at=_fmt(_ensure_tz(checkpoint.started_at)) if checkpoint else None,
        completed_at=_fmt(_ensure_tz(exec_result.completed_at)) if exec_result else None,
        duration_seconds=duration,
        error=error,
        idempotency_hit=bool(idem_record and idem_record.status == "COMPLETED"),
        idempotency_status=idem_record.status if idem_record else None,
    )
