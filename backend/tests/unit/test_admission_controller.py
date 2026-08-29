"""Unit Tests for AdmissionController Service.

Validates parameter type checking and decision delegation.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, ValueAssessment, CapacityState
from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum
from app.admission.controller import AdmissionController


def test_admission_controller_type_validation():
    controller = AdmissionController()
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        raw_payload={"test": "data"},
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
    capacity = CapacityState()

    # Valid call
    decision = controller.evaluate_admission(event, assessment, capacity, evaluation_time=now)
    assert decision.decision == AdmissionDecisionEnum.ADMIT

    # Invalid work item type
    with pytest.raises(TypeError):
        controller.evaluate_admission("invalid_item", assessment, capacity)

    # Invalid capacity type
    with pytest.raises(TypeError):
        controller.evaluate_admission(event, assessment, "invalid_capacity")
