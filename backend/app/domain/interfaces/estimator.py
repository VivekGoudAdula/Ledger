"""Value Estimator Interface Protocol.

Provides provider-independent protocol for estimating signal/incident work item value.
"""

from typing import Protocol, runtime_checkable
from app.domain.models import SignalEvent, CoalescedIncident, ValueAssessment


@runtime_checkable
class ValueEstimatorInterface(Protocol):
    """Protocol for work item value estimators (RuleBased or AI-backed)."""

    async def estimate(
        self, work_item: SignalEvent | CoalescedIncident
    ) -> ValueAssessment:
        """Estimate value dimensions (urgency, confidence, consequence, compute cost)."""
        ...
