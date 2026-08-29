"""Integration Test: Dynamic Arrival Priority & Value-Aware Scheduling.

Verifies that when lower-value items arrive first, a subsequent high-value critical event
is prioritized by backend effective_priority evaluation over arrival order.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.domain.models import SignalEvent, CapacityState, TenantState
from app.domain.enums import SeverityLevel, EventStatus
from app.admission.controller import AdmissionController
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.storage.repositories import EventRepository, ExecutionRepository
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService
from app.api.routes.queue import get_queue_state


@pytest.mark.asyncio
async def test_dynamic_arrival_prioritizes_high_value_over_arrival_order(db_session):
    now = datetime.now(timezone.utc)
    event_repo = EventRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    broker = InMemoryWorkQueue(stream_name="ledger:dynamic_stream", group_name="dynamic_workers")
    publisher_service = QueuePublisherService(broker=broker, event_repo=event_repo)
    val_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), mode="rule_based")
    adm_controller = AdmissionController()

    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="tenant_dynamic", quota=100.0)

    # 1. Enqueue early low/medium-value item
    early_medium_evt = SignalEvent(
        source_type="github", source_id="early_med", tenant_id="tenant_dynamic",
        payload_hash="a" * 64, coalesce_key="k_early", event_type="issue_opened",
        severity=SeverityLevel.MEDIUM, raw_payload={"id": "early"},
        created_at=now - timedelta(seconds=10),
    )
    await event_repo.save(early_medium_evt)

    assessment_early = await val_service.assess_work_item(early_medium_evt)
    decision_early = adm_controller.evaluate_admission(early_medium_evt, assessment_early, capacity, tenant, evaluation_time=now)
    await publisher_service.handle_admission_decision(early_medium_evt, decision_early)
    await event_repo.update_admission_scores(
        event_id=early_medium_evt.event_id,
        urgency=assessment_early.urgency,
        confidence=assessment_early.confidence,
        consequence=assessment_early.consequence_of_drop,
        compute_cost=assessment_early.estimated_compute_cost,
        admission_score=assessment_early.expected_value,
        admission_decision=decision_early.decision.value,
        admission_reason=decision_early.reason.value,
    )

    # 2. Dynamically inject late critical-value item
    late_critical_evt = SignalEvent(
        source_type="status_feed", source_id="late_crit", tenant_id="tenant_dynamic",
        payload_hash="b" * 64, coalesce_key="k_late", event_type="database_outage",
        severity=SeverityLevel.CRITICAL, raw_payload={"id": "late_crit"},
        created_at=now,
    )
    await event_repo.save(late_critical_evt)

    assessment_late = await val_service.assess_work_item(late_critical_evt)
    decision_late = adm_controller.evaluate_admission(late_critical_evt, assessment_late, capacity, tenant, evaluation_time=now)
    await publisher_service.handle_admission_decision(late_critical_evt, decision_late)
    await event_repo.update_admission_scores(
        event_id=late_critical_evt.event_id,
        urgency=assessment_late.urgency,
        confidence=assessment_late.confidence,
        consequence=assessment_late.consequence_of_drop,
        compute_cost=assessment_late.estimated_compute_cost,
        admission_score=assessment_late.expected_value,
        admission_decision=decision_late.decision.value,
        admission_reason=decision_late.reason.value,
    )

    await db_session.commit()

    # 3. Query queue state through get_queue_state API
    q_state = await get_queue_state(event_repo=event_repo)

    assert len(q_state.ready_queue) == 2

    # 4. Verify backend scheduling order: late critical event MUST be position 1 (higher effective priority)
    first_item = q_state.ready_queue[0]
    second_item = q_state.ready_queue[1]

    assert first_item.event_id == late_critical_evt.event_id
    assert second_item.event_id == early_medium_evt.event_id
    assert first_item.effective_priority > second_item.effective_priority
