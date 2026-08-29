"""Unit Tests for Admission Domain Entities.

Validates capacity boundary constraints, tenant quota parameters, and decision schemas.
"""

from datetime import datetime, timezone
import pytest

from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum, AdmissionReason
from app.domain.models import CapacityState, TenantState, AdmissionDecision


def test_valid_capacity_state_accepted():
    cap = CapacityState(total_capacity=100.0, available_capacity=50.0, active_compute=50.0)
    assert cap.total_capacity == 100.0
    assert cap.available_capacity == 50.0


@pytest.mark.parametrize("invalid_val", [-10.0, float("nan"), float("inf")])
def test_negative_or_non_finite_capacity_rejected(invalid_val):
    with pytest.raises(ValueError):
        CapacityState(total_capacity=100.0, available_capacity=invalid_val)


def test_available_capacity_exceeding_total_rejected():
    with pytest.raises(ValueError, match="cannot exceed total_capacity"):
        CapacityState(total_capacity=50.0, available_capacity=100.0)


def test_valid_tenant_state_accepted():
    tenant = TenantState(tenant_id="tenant_x", current_usage=10.0, quota=50.0)
    assert tenant.tenant_id == "tenant_x"
    assert tenant.current_usage == 10.0


def test_naive_evaluated_at_rejected():
    naive_time = datetime.now()
    with pytest.raises(ValueError, match="timezone-aware"):
        AdmissionDecision(
            decision=AdmissionDecisionEnum.ADMIT,
            work_item_id="item_1",
            reason=AdmissionReason.ADMITTED_CAPACITY_AVAILABLE,
            effective_value=0.8,
            value_per_compute=1.0,
            capacity_required=1.0,
            capacity_available=50.0,
            tenant_id="tenant_a",
            explanation="test",
            evaluated_at=naive_time,
        )
