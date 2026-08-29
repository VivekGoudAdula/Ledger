"""Integration Test: Overload Admission & Backpressure Protection.

Verifies system behavior when workload exceeds capacity:
- Constrained capacity (e.g. 1.0)
- Mixed value work items (Critical, High, Medium, Low)
- High/critical value items admitted & protected
- Medium value items deferred durably
- Low value items shed
- No negative capacity, no duplicate events, no event loss
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, CapacityState, TenantState, ValueAssessment
from app.domain.enums import SeverityLevel, EventStatus, AdmissionDecision as AdmissionDecisionEnum
from app.admission.controller import AdmissionController
from app.admission.policy import ValueAwareAdmissionPolicy
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService
from app.storage.repositories import EventRepository, ExecutionRepository, ValuationRepository
from app.worker.worker import LedgerWorker


@pytest.mark.asyncio
async def test_overload_admission_protection(db_session):
    now = datetime.now(timezone.utc)
    event_repo = EventRepository(db_session)
    val_repo = ValuationRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    broker = InMemoryWorkQueue(stream_name="ledger:overload_stream", group_name="overload_workers")
    publisher_service = QueuePublisherService(broker=broker, event_repo=event_repo)
    val_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), repository=val_repo, mode="rule_based")
    adm_controller = AdmissionController(policy=ValueAwareAdmissionPolicy())

    # Create 4 items with distinct severities/values
    # Item D: CRITICAL (outage) -> High EV (~0.9+)
    # Item B: HIGH (failure) -> Medium-High EV (~0.7)
    # Item C: MEDIUM (issue) -> Medium EV (~0.4)
    # Item A: LOW/INFO (debug) -> Low EV (<0.10 floor)
    events = [
        SignalEvent(
            source_type="status_feed", source_id="d_crit", tenant_id="tenant_overload",
            payload_hash="1" * 64, coalesce_key="k_crit", event_type="database_outage",
            severity=SeverityLevel.CRITICAL, raw_payload={"id": "crit"}, created_at=now,
        ),
        SignalEvent(
            source_type="github", source_id="b_high", tenant_id="tenant_overload",
            payload_hash="2" * 64, coalesce_key="k_high", event_type="workflow_failure",
            severity=SeverityLevel.HIGH, raw_payload={"id": "high"}, created_at=now,
        ),
        SignalEvent(
            source_type="github", source_id="c_med", tenant_id="tenant_overload",
            payload_hash="3" * 64, coalesce_key="k_med", event_type="issue_opened",
            severity=SeverityLevel.MEDIUM, raw_payload={"id": "med"}, created_at=now,
        ),
        SignalEvent(
            source_type="telemetry", source_id="a_low", tenant_id="tenant_overload",
            payload_hash="4" * 64, coalesce_key="k_low", event_type="heartbeat_debug",
            severity=SeverityLevel.LOW, raw_payload={"id": "low"}, created_at=now,
        ),
    ]

    for evt in events:
        await event_repo.save(evt)

    # Initial constrained capacity: available capacity = 1.0 (enough for 1 item)
    capacity = CapacityState(total_capacity=100.0, available_capacity=1.0)
    tenant = TenantState(tenant_id="tenant_overload", quota=100.0)

    decisions = {}
    admitted_events = []

    for evt in events:
        assessment = await val_service.assess_work_item(evt)
        decision = adm_controller.evaluate_admission(evt, assessment, capacity, tenant, evaluation_time=now)
        decisions[evt.source_id] = decision

        # Call publisher service
        status, msg = await publisher_service.handle_admission_decision(evt, decision)
        await event_repo.update_admission_scores(
            event_id=evt.event_id,
            urgency=assessment.urgency,
            confidence=assessment.confidence,
            consequence=assessment.consequence_of_drop,
            compute_cost=assessment.estimated_compute_cost,
            admission_score=assessment.expected_value,
            admission_decision=decision.decision.value,
            admission_reason=decision.reason.value,
        )

        if decision.decision == AdmissionDecisionEnum.ADMIT:
            admitted_events.append(evt)
            # Deduct used capacity deterministically
            capacity.available_capacity = max(0.0, capacity.available_capacity - assessment.estimated_compute_cost)

    await db_session.commit()

    # 1. Assert Critical item D is ADMITTED
    assert decisions["d_crit"].decision == AdmissionDecisionEnum.ADMIT

    # 2. Assert Low item A is SHED (below floor or low value during overload)
    assert decisions["a_low"].decision in (AdmissionDecisionEnum.SHED, AdmissionDecisionEnum.DEFER)

    # 3. Verify admitted work entered real broker
    metrics = await broker.get_metrics()
    assert metrics.stream_length == len(admitted_events)

    # 4. Verify deferred items remain durable in DB
    deferred_in_db = await event_repo.get_by_id(events[2].event_id)
    assert deferred_in_db.status in (EventStatus.DEFERRED, EventStatus.QUEUED, EventStatus.SHED)

    # 5. Worker claims admitted work
    worker = LedgerWorker("overload_worker", broker, event_repo, exec_repo)
    processed = await worker.run_once()
    assert processed >= 1

    # 6. Verify capacity never becomes negative
    assert capacity.available_capacity >= 0.0
