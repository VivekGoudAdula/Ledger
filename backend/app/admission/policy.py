"""Value-Aware Admission Control Policy Engine.

Implements deterministic admission rules (ADMIT, DEFER, SHED) incorporating value density,
aging starvation prevention, deadline proximity, tenant quotas, and capacity limits.
"""

from datetime import datetime, timezone, timedelta
from app.config import settings
from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum, AdmissionReason
from app.domain.models import (
    SignalEvent,
    CoalescedIncident,
    ValueAssessment,
    CapacityState,
    TenantState,
    AdmissionDecision,
)
from app.domain.interfaces.admission import AdmissionPolicyInterface


class ValueAwareAdmissionPolicy(AdmissionPolicyInterface):
    """Deterministic admission policy reasoning over value, cost, aging, tenant quotas, and capacity."""

    def __init__(
        self,
        base_value_floor: float = 0.10,
        high_value_threshold: float = 0.80,
        policy_version: str = "admission_policy_v1",
    ) -> None:
        self._base_value_floor = base_value_floor
        self._high_value_threshold = high_value_threshold
        self._policy_version = policy_version

    def evaluate(
        self,
        work_item: SignalEvent | CoalescedIncident,
        assessment: ValueAssessment,
        capacity: CapacityState,
        tenant: TenantState | None = None,
        evaluation_time: datetime | None = None,
    ) -> AdmissionDecision:
        """Evaluate deterministic admission decision (ADMIT, DEFER, SHED)."""
        now = evaluation_time or datetime.now(timezone.utc)
        work_id = work_item.event_id if isinstance(work_item, SignalEvent) else work_item.incident_id
        tenant_id = work_item.tenant_id
        cost = assessment.estimated_compute_cost

        # 1. Deadline Expiration Rule
        deadline = work_item.deadline_at if isinstance(work_item, SignalEvent) else None
        if deadline and now >= deadline:
            return AdmissionDecision(
                decision=AdmissionDecisionEnum.SHED,
                work_item_id=work_id,
                reason=AdmissionReason.SHED_DEADLINE_EXPIRED,
                effective_value=0.0,
                value_per_compute=0.0,
                capacity_required=cost,
                capacity_available=capacity.available_capacity,
                tenant_id=tenant_id,
                explanation=f"Work item expired at {deadline.isoformat()} prior to evaluation",
                policy_version=self._policy_version,
                evaluated_at=now,
            )

        # 2. Aging & Starvation Prevention
        created_at = work_item.created_at if isinstance(work_item, SignalEvent) else work_item.first_seen
        waiting_seconds = max(0.0, (now - created_at).total_seconds())
        aging_bonus = min(0.30, waiting_seconds * 0.001)  # Max +0.30 bonus for aging
        effective_val = round(min(1.0, assessment.expected_value + aging_bonus), 4)
        value_density = round(effective_val / max(cost, 0.01), 4)

        # 3. Absolute Value Floor Rule
        if effective_val < self._base_value_floor:
            is_overloaded = capacity.available_capacity < (capacity.total_capacity * 0.20)
            reason = AdmissionReason.SHED_LOW_VALUE_DURING_OVERLOAD if is_overloaded else AdmissionReason.SHED_BELOW_VALUE_FLOOR
            return AdmissionDecision(
                decision=AdmissionDecisionEnum.SHED,
                work_item_id=work_id,
                reason=reason,
                effective_value=effective_val,
                value_per_compute=value_density,
                capacity_required=cost,
                capacity_available=capacity.available_capacity,
                tenant_id=tenant_id,
                explanation=f"Effective expected value {effective_val} below floor threshold {self._base_value_floor}",
                policy_version=self._policy_version,
                evaluated_at=now,
            )

        # 4. Tenant Quota Fair-Share Guardrail
        if tenant and (tenant.current_usage + cost) > tenant.quota:
            return AdmissionDecision(
                decision=AdmissionDecisionEnum.DEFER,
                work_item_id=work_id,
                reason=AdmissionReason.DEFERRED_TENANT_QUOTA,
                effective_value=effective_val,
                value_per_compute=value_density,
                capacity_required=cost,
                capacity_available=capacity.available_capacity,
                tenant_id=tenant_id,
                explanation=f"Tenant '{tenant_id}' quota exceeded: usage {tenant.current_usage} + cost {cost} > quota {tenant.quota}",
                policy_version=self._policy_version,
                defer_until=now + timedelta(seconds=30),
                evaluated_at=now,
            )

        # 5. System Capacity Allocation Rule
        if capacity.available_capacity >= cost:
            is_high_val = effective_val >= self._high_value_threshold
            reason = AdmissionReason.ADMITTED_HIGH_VALUE if is_high_val else AdmissionReason.ADMITTED_CAPACITY_AVAILABLE
            return AdmissionDecision(
                decision=AdmissionDecisionEnum.ADMIT,
                work_item_id=work_id,
                reason=reason,
                effective_value=effective_val,
                value_per_compute=value_density,
                capacity_required=cost,
                capacity_available=capacity.available_capacity,
                tenant_id=tenant_id,
                explanation=f"Admitted: required compute {cost} <= available capacity {capacity.available_capacity} (effective EV: {effective_val})",
                policy_version=self._policy_version,
                evaluated_at=now,
            )

        # Capacity Exhausted -> Defer
        return AdmissionDecision(
            decision=AdmissionDecisionEnum.DEFER,
            work_item_id=work_id,
            reason=AdmissionReason.DEFERRED_CAPACITY_EXHAUSTED,
            effective_value=effective_val,
            value_per_compute=value_density,
            capacity_required=cost,
            capacity_available=capacity.available_capacity,
            tenant_id=tenant_id,
            explanation=f"Deferred: required compute {cost} exceeds available capacity {capacity.available_capacity}",
            policy_version=self._policy_version,
            defer_until=now + timedelta(seconds=15),
            evaluated_at=now,
        )
