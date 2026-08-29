"""Admission Controller Application Service.

Orchestrates deterministic admission control evaluation between value estimation and capacity allocation.
"""

from datetime import datetime, timezone
import logging

from app.domain.models import (
    SignalEvent,
    CoalescedIncident,
    ValueAssessment,
    CapacityState,
    TenantState,
    AdmissionDecision,
)
from app.domain.interfaces.admission import AdmissionPolicyInterface
from app.admission.policy import ValueAwareAdmissionPolicy

logger = logging.getLogger(__name__)


class AdmissionController:
    """Application-level service orchestrating work item admission evaluations."""

    def __init__(
        self,
        policy: AdmissionPolicyInterface | None = None,
    ) -> None:
        self._policy = policy or ValueAwareAdmissionPolicy()

    def evaluate_admission(
        self,
        work_item: SignalEvent | CoalescedIncident,
        assessment: ValueAssessment,
        capacity: CapacityState,
        tenant: TenantState | None = None,
        evaluation_time: datetime | None = None,
    ) -> AdmissionDecision:
        """Evaluate deterministic admission decision for work item.

        Returns:
            AdmissionDecision (ADMIT, DEFER, SHED)
        """
        if not isinstance(work_item, (SignalEvent, CoalescedIncident)):
            raise TypeError(f"Invalid work_item type: {type(work_item)}")
        if not isinstance(assessment, ValueAssessment):
            raise TypeError(f"Invalid assessment type: {type(assessment)}")
        if not isinstance(capacity, CapacityState):
            raise TypeError(f"Invalid capacity type: {type(capacity)}")

        now = evaluation_time or datetime.now(timezone.utc)

        decision = self._policy.evaluate(
            work_item=work_item,
            assessment=assessment,
            capacity=capacity,
            tenant=tenant,
            evaluation_time=now,
        )

        logger.info(
            "Admission Decision [%s]: work_item_id=%s, decision=%s, reason=%s, EV=%.4f",
            decision.policy_version,
            decision.work_item_id,
            decision.decision.value,
            decision.reason.value,
            decision.effective_value,
        )

        return decision
