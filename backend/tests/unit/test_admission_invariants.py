"""Unit Tests for Admission Controller Invariants.

Verifies deterministic capacity bounds, decision exclusivity, and score range invariants.
"""

from datetime import datetime, timezone, timedelta

from app.domain.models import SignalEvent, ValueAssessment, CapacityState, TenantState
from app.domain.enums import DecisionType, SeverityLevel
from app.admission.controller import AdmissionController


def test_admission_invariant_admitted_compute_bounded_by_capacity():
    controller = AdmissionController()
    now = datetime.now(timezone.utc)
    capacity = CapacityState(total_capacity=100.0, available_capacity=10.0)
    tenant = TenantState(tenant_id="tenant_inv", quota=100.0)

    # Item requesting 25.0 compute cost > 10.0 available
    evt = SignalEvent(
        source_type="test",
        source_id="inv_1",
        tenant_id="tenant_inv",
        payload_hash="hash_inv_1",
        coalesce_key="key_inv_1",
        raw_payload={},
        created_at=now,
        deadline_at=now + timedelta(seconds=60),
    )
    assessment = ValueAssessment(
        work_item_id="inv_1",
        work_item_type="signal",
        urgency=0.5,
        confidence=0.9,
        consequence_of_drop=0.5,
        estimated_compute_cost=25.0,
        rationale="Invariant check",
        expected_value=0.5,
        value_per_compute=0.02,
        deadline=evt.deadline_at,
    )

    decision = controller.evaluate_admission(evt, assessment, capacity, tenant, now)

    # Must be DEFER or SHED (cannot be ADMIT when compute exceeds capacity)
    assert decision.decision != DecisionType.ADMIT


def test_admission_invariant_decision_exclusivity():
    controller = AdmissionController()
    now = datetime.now(timezone.utc)
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="tenant_inv", quota=100.0)

    evt = SignalEvent(
        source_type="test",
        source_id="inv_2",
        tenant_id="tenant_inv",
        payload_hash="hash_inv_2",
        coalesce_key="key_inv_2",
        raw_payload={},
        created_at=now,
        deadline_at=now + timedelta(seconds=60),
    )
    assessment = ValueAssessment(
        work_item_id="inv_2",
        work_item_type="signal",
        urgency=0.9,
        confidence=0.9,
        consequence_of_drop=0.9,
        estimated_compute_cost=0.5,
        rationale="Invariant check",
        expected_value=0.9,
        value_per_compute=1.8,
        deadline=evt.deadline_at,
    )

    decision = controller.evaluate_admission(evt, assessment, capacity, tenant, now)
    assert decision.decision in (DecisionType.ADMIT, DecisionType.DEFER, DecisionType.SHED)
    assert isinstance(decision.effective_value, float)
    assert 0.0 <= decision.effective_value <= 1.0
