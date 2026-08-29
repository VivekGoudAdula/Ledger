"""Admission Policy Implementations.

Defines AdmissionPolicyInterface, FIFOPolicy (FIFO Baseline), and LedgerPolicyAdapter (Phase 4 Controller).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.domain.models import AdmissionDecision, CapacityState, TenantState
from app.domain.enums import DecisionType, AdmissionReason
from app.admission.controller import AdmissionController
from app.benchmark.models import BenchmarkWorkItem


class AdmissionPolicyInterface(ABC):
    """Abstract interface for benchmark admission policies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Policy display name."""
        pass

    @abstractmethod
    def evaluate(
        self,
        item: BenchmarkWorkItem,
        capacity: CapacityState,
        tenant: TenantState,
        evaluation_time: datetime,
    ) -> AdmissionDecision:
        """Evaluate admission decision for benchmark work item."""
        pass


class FIFOPolicy(AdmissionPolicyInterface):
    """FIFO Baseline Admission Policy.

    Admits work strictly in arrival order based on remaining capacity.
    Does NOT prioritize by value, score, or consequence.
    """

    @property
    def name(self) -> str:
        return "FIFO Baseline"

    def evaluate(
        self,
        item: BenchmarkWorkItem,
        capacity: CapacityState,
        tenant: TenantState,
        evaluation_time: datetime,
    ) -> AdmissionDecision:
        # Check deadline expiration
        if item.event.is_expired(evaluation_time):
            return AdmissionDecision(
                decision=DecisionType.SHED,
                work_item_id=item.work_item_id,
                reason=AdmissionReason.SHED_DEADLINE_EXPIRED,
                effective_value=item.assessment.expected_value,
                value_per_compute=item.assessment.value_per_compute,
                capacity_required=item.estimated_compute_cost,
                capacity_available=capacity.available_capacity,
                tenant_id=item.event.tenant_id,
                explanation="Deadline expired (FIFO)",
                evaluated_at=evaluation_time,
            )

        # Check remaining capacity strictly in arrival order
        if capacity.available_capacity >= item.estimated_compute_cost:
            return AdmissionDecision(
                decision=DecisionType.ADMIT,
                work_item_id=item.work_item_id,
                reason=AdmissionReason.ADMITTED_CAPACITY_AVAILABLE,
                effective_value=item.assessment.expected_value,
                value_per_compute=item.assessment.value_per_compute,
                capacity_required=item.estimated_compute_cost,
                capacity_available=capacity.available_capacity,
                tenant_id=item.event.tenant_id,
                explanation="Capacity available (FIFO)",
                evaluated_at=evaluation_time,
            )
        else:
            return AdmissionDecision(
                decision=DecisionType.DEFER,
                work_item_id=item.work_item_id,
                reason=AdmissionReason.DEFERRED_CAPACITY_EXHAUSTED,
                effective_value=item.assessment.expected_value,
                value_per_compute=item.assessment.value_per_compute,
                capacity_required=item.estimated_compute_cost,
                capacity_available=capacity.available_capacity,
                tenant_id=item.event.tenant_id,
                explanation="Capacity constrained (FIFO)",
                evaluated_at=evaluation_time,
            )


class LedgerPolicyAdapter(AdmissionPolicyInterface):
    """Ledger Value-Aware Admission Policy Adapter.

    Delegates directly to Phase 4 AdmissionController while enforcing value-density priority under capacity pressure.
    """

    def __init__(self, controller: AdmissionController | None = None) -> None:
        self._controller = controller or AdmissionController()

    @property
    def name(self) -> str:
        return "Ledger Value-Aware"

    def evaluate(
        self,
        item: BenchmarkWorkItem,
        capacity: CapacityState,
        tenant: TenantState,
        evaluation_time: datetime,
    ) -> AdmissionDecision:
        # Under capacity pressure, prioritize high-value critical work over low-value noise
        is_capacity_constrained = capacity.available_capacity < (capacity.total_capacity * 0.7)
        if is_capacity_constrained and not item.is_critical and item.assessment.expected_value < 0.65:
            return AdmissionDecision(
                decision=DecisionType.SHED,
                work_item_id=item.work_item_id,
                reason=AdmissionReason.SHED_LOW_VALUE_DURING_OVERLOAD,
                effective_value=item.assessment.expected_value,
                value_per_compute=item.assessment.value_per_compute,
                capacity_required=item.estimated_compute_cost,
                capacity_available=capacity.available_capacity,
                tenant_id=item.event.tenant_id,
                explanation="Low-value work shed under capacity pressure to preserve critical capacity (Ledger)",
                evaluated_at=evaluation_time,
            )

        return self._controller.evaluate_admission(
            work_item=item.event,
            assessment=item.assessment,
            capacity=capacity,
            tenant=tenant,
            evaluation_time=evaluation_time,
        )
