"""Unit Tests for ValueAssessment Domain Entity.

Validates score bound checks, compute cost constraints, timestamp timezone-awareness,
and deterministic expected_value and value_per_compute calculations.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.domain.models import ValueAssessment


def test_valid_value_assessment_accepted():
    now = datetime.now(timezone.utc)
    assessment = ValueAssessment(
        work_item_id="item_123",
        work_item_type="signal",
        urgency=0.8,
        confidence=0.9,
        consequence_of_drop=0.85,
        estimated_compute_cost=1.5,
        rationale="Critical alert test",
        estimated_at=now,
    )
    assert assessment.urgency == 0.8
    assert assessment.confidence == 0.9
    assert assessment.consequence_of_drop == 0.85
    assert assessment.estimated_compute_cost == 1.5


@pytest.mark.parametrize("invalid_score", [-0.1, 1.1, float("nan"), float("inf")])
def test_out_of_bound_scores_rejected(invalid_score):
    with pytest.raises(ValueError):
        ValueAssessment(
            work_item_id="item_err",
            work_item_type="signal",
            urgency=invalid_score,
            confidence=0.5,
            consequence_of_drop=0.5,
            estimated_compute_cost=1.0,
            rationale="err",
        )


@pytest.mark.parametrize("invalid_cost", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_compute_cost_rejected(invalid_cost):
    with pytest.raises(ValueError):
        ValueAssessment(
            work_item_id="item_cost_err",
            work_item_type="signal",
            urgency=0.5,
            confidence=0.5,
            consequence_of_drop=0.5,
            estimated_compute_cost=invalid_cost,
            rationale="err",
        )


def test_naive_timestamp_rejected():
    naive_time = datetime.now()  # Naive (no tz)
    with pytest.raises(ValueError, match="timezone-aware"):
        ValueAssessment(
            work_item_id="item_tz",
            work_item_type="signal",
            urgency=0.5,
            confidence=0.5,
            consequence_of_drop=0.5,
            estimated_compute_cost=1.0,
            rationale="tz test",
            estimated_at=naive_time,
        )


def test_expected_value_formula_calculation():
    # High urgency (0.9), high consequence (0.9), high confidence (1.0)
    ev_high = ValueAssessment.compute_expected_value(
        urgency=0.9,
        confidence=1.0,
        consequence_of_drop=0.9,
    )
    assert 0.70 <= ev_high <= 0.85

    # Same urgency/consequence, but lower confidence (0.2)
    ev_low_conf = ValueAssessment.compute_expected_value(
        urgency=0.9,
        confidence=0.2,
        consequence_of_drop=0.9,
    )
    assert ev_low_conf < ev_high


def test_expired_deadline_produces_zero_expected_value():
    now = datetime.now(timezone.utc)
    expired_deadline = now - timedelta(minutes=5)

    ev = ValueAssessment.compute_expected_value(
        urgency=0.9,
        confidence=0.9,
        consequence_of_drop=0.9,
        deadline=expired_deadline,
        reference_time=now,
    )
    assert ev == 0.0


def test_value_per_compute_calculation():
    # High EV (0.8), low compute cost (0.2) -> high V/COMP (4.0)
    ratio_high = ValueAssessment.compute_value_per_compute(expected_value=0.8, estimated_compute_cost=0.2)
    assert ratio_high == 4.0

    # Division by zero safety: zero/tiny cost defaults to safe cost 0.01
    ratio_zero_cost = ValueAssessment.compute_value_per_compute(expected_value=0.5, estimated_compute_cost=0.0)
    assert ratio_zero_cost == 50.0
