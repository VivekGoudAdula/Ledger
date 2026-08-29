"""Deterministic Execution Handler.

Provides concrete deterministic processing analysis over SignalEvents and CoalescedIncidents.
"""

from typing import Any
from datetime import datetime, timezone
import hashlib

from app.domain.models import SignalEvent, CoalescedIncident, ValueAssessment
from app.domain.interfaces.execution import ExecutionHandlerInterface


class DeterministicExecutionHandler(ExecutionHandlerInterface):
    """Deterministic task handler producing structured business execution analysis outputs."""

    async def execute(
        self,
        work_item: SignalEvent | CoalescedIncident,
        assessment: ValueAssessment | None = None,
    ) -> dict[str, Any]:
        """Execute deterministic analysis over work item."""
        now = datetime.now(timezone.utc)

        if isinstance(work_item, SignalEvent):
            payload_str = str(work_item.raw_payload)
            digest = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
            return {
                "work_type": "signal_event",
                "event_id": work_item.event_id,
                "tenant_id": work_item.tenant_id,
                "severity": work_item.severity.value,
                "payload_sha256": digest,
                "expected_value": assessment.expected_value if assessment else None,
                "processed_at": now.isoformat(),
                "action_taken": f"Analyzed signal '{work_item.event_type}' for tenant '{work_item.tenant_id}'",
            }
        elif isinstance(work_item, CoalescedIncident):
            return {
                "work_type": "coalesced_incident",
                "incident_id": work_item.incident_id,
                "tenant_id": work_item.tenant_id,
                "signal_count": work_item.signal_count,
                "coalesce_key": work_item.coalesce_key,
                "expected_value": assessment.expected_value if assessment else None,
                "processed_at": now.isoformat(),
                "action_taken": f"Aggregated incident with {work_item.signal_count} linked signals",
            }
        else:
            raise TypeError(f"Unsupported work_item type: {type(work_item)}")
