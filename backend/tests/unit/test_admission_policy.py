"""Unit Tests for ValueAwareAdmissionPolicy.

Validates capacity limits, overload shedding, tenant quotas, deadline expiration,
starvation prevention aging, and policy monotonicity.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.domain.models import (
    SignalEvent,
    ValueAssessment,
    CapacityState,
    TenantState,
)
from app.domain.enums import SeverityLevel, AdmissionDecision as AdmissionDecisionEnum, AdmissionReason
from app.admission.policy import ValueAwareAdmissionPolicy


def test_capacity_available_admits_work():
    policy = ValueAwareAdmissionPolicy()
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        raw_payload={"test": "data"},
        created_at=now,
    )

    assessment = ValueAssessment(
        work_item_id=event.event_id,
        work_item_type="signal",
        urgency=0.5,
        confidence=0.9,
        consequence_of_drop=0.5,
        estimated_compute_cost=1.0,
        expected_value=0.5,
        value_per_compute=0.5,
        rationale="test",
    )

    capacity = CapacityState(total_capacity=100.0, available_capacity=50.0)

    decision = policy.evaluate(event, assessment, capacity, evaluation_time=now)
    assert decision.decision == AdmissionDecisionEnum.ADMIT
    assert decision.reason == AdmissionReason.ADMITTED_CAPACITY_AVAILABLE


def test_insufficient_capacity_defers_work():
    policy = ValueAwareAdmissionPolicy()
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="2",
        tenant_id="t1",
        payload_hash="b" * 64,
        coalesce_key="k2",
        raw_payload={"test": "data"},
        created_at=now,
    )

    assessment = ValueAssessment(
        work_item_id=event.event_id,
        work_item_type="signal",
        urgency=0.8,
        confidence=0.9,
        consequence_of_drop=0.8,
        estimated_compute_cost=10.0,
        expected_value=0.75,
        value_per_compute=0.075,
        rationale="test",
    )

    capacity = CapacityState(total_capacity=100.0, available_capacity=2.0)  # Only 2.0 available < 10.0 cost

    decision = policy.evaluate(event, assessment, capacity, evaluation_time=now)
    assert decision.decision == AdmissionDecisionEnum.DEFER
    assert decision.reason == AdmissionReason.DEFERRED_CAPACITY_EXHAUSTED


def test_expired_deadline_sheds_work():
    policy = ValueAwareAdmissionPolicy()
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="3",
        tenant_id="t1",
        payload_hash="c" * 64,
        coalesce_key="k3",
        deadline_at=now - timedelta(seconds=1),  # Expired
        raw_payload={"test": "data"},
        created_at=now - timedelta(minutes=10),
    )

    assessment = ValueAssessment(
        work_item_id=event.event_id,
        work_item_type="signal",
        urgency=0.9,
        confidence=0.9,
        consequence_of_drop=0.9,
        estimated_compute_cost=1.0,
        expected_value=0.0,
        value_per_compute=0.0,
        rationale="expired",
    )

    capacity = CapacityState(total_capacity=100.0, available_capacity=50.0)

    decision = policy.evaluate(event, assessment, capacity, evaluation_time=now)
    assert decision.decision == AdmissionDecisionEnum.SHED
    assert decision.reason == AdmissionReason.SHED_DEADLINE_EXPIRED


def test_tenant_quota_exceeded_defers_work():
    policy = ValueAwareAdmissionPolicy()
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="4",
        tenant_id="t_quota",
        payload_hash="d" * 64,
        coalesce_key="k4",
        raw_payload={"test": "data"},
        created_at=now,
    )

    assessment = ValueAssessment(
        work_item_id=event.event_id,
        work_item_type="signal",
        urgency=0.8,
        confidence=0.9,
        consequence_of_drop=0.8,
        estimated_compute_cost=5.0,
        expected_value=0.7,
        value_per_compute=0.14,
        rationale="test",
    )

    capacity = CapacityState(total_capacity=100.0, available_capacity=50.0)
    tenant = TenantState(tenant_id="t_quota", current_usage=48.0, quota=50.0)  # 48 + 5 > 50 quota!

    decision = policy.evaluate(event, assessment, capacity, tenant=tenant, evaluation_time=now)
    assert decision.decision == AdmissionDecisionEnum.DEFER
    assert decision.reason == AdmissionReason.DEFERRED_TENANT_QUOTA


def test_starvation_prevention_aging():
    policy = ValueAwareAdmissionPolicy()
    now = datetime.now(timezone.utc)

    # Work item created 10 minutes ago
    old_event = SignalEvent(
        source_type="github",
        source_id="5",
        tenant_id="t1",
        payload_hash="e" * 64,
        coalesce_key="k5",
        raw_payload={"test": "data"},
        created_at=now - timedelta(minutes=10),  # 600s waiting -> +0.30 aging bonus
    )

    assessment = ValueAssessment(
        work_item_id=old_event.event_id,
        work_item_type="signal",
        urgency=0.5,
        confidence=0.8,
        consequence_of_drop=0.5,
        estimated_compute_cost=1.0,
        expected_value=0.40,
        value_per_compute=0.40,
        rationale="old item",
    )

    capacity = CapacityState(total_capacity=100.0, available_capacity=50.0)

    decision = policy.evaluate(old_event, assessment, capacity, evaluation_time=now)
    assert decision.effective_value == 0.70  # 0.40 + 0.30 aging bonus!
