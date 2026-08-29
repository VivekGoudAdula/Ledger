"""Admission Policy Interface Protocol.

Provides a protocol for deterministic admission control policies.
"""

from typing import Protocol, runtime_checkable
from datetime import datetime

from app.domain.models import (
    SignalEvent,
    CoalescedIncident,
    ValueAssessment,
    CapacityState,
    TenantState,
    AdmissionDecision,
)


@runtime_checkable
class AdmissionPolicyInterface(Protocol):
    """Protocol interface for admission policies evaluating work items against capacity."""

    def evaluate(
        self,
        work_item: SignalEvent | CoalescedIncident,
        assessment: ValueAssessment,
        capacity: CapacityState,
        tenant: TenantState | None = None,
        evaluation_time: datetime | None = None,
    ) -> AdmissionDecision:
        """Evaluate deterministic admission decision (ADMIT, DEFER, SHED)."""
        ...
