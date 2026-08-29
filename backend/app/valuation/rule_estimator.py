"""Rule-Based Value Estimator.

Provides guaranteed offline, deterministic signal valuation policies without network dependencies.
"""

import json
from app.domain.models import SignalEvent, CoalescedIncident, ValueAssessment
from app.domain.interfaces.estimator import ValueEstimatorInterface


class RuleBasedValueEstimator(ValueEstimatorInterface):
    """Deterministic rule-based estimator analyzing severity, categories, payload size, and coalescing."""

    def __init__(self, policy_version: str = "rule_based_v1") -> None:
        self._policy_version = policy_version

    async def estimate(
        self, work_item: SignalEvent | CoalescedIncident
    ) -> ValueAssessment:
        """Estimate value dimensions (urgency, confidence, consequence, compute cost)."""
        if isinstance(work_item, SignalEvent):
            return self._estimate_signal(work_item)
        elif isinstance(work_item, CoalescedIncident):
            return self._estimate_incident(work_item)
        else:
            raise TypeError(f"Unsupported work_item type: {type(work_item)}")

    def _estimate_signal(self, event: SignalEvent) -> ValueAssessment:
        """Estimate value for single SignalEvent."""
        urgency = self._map_severity_to_urgency(event.severity.value)
        confidence = 0.95 if event.source_type != "generic" else 0.70

        # Assess consequence of drop from keywords and source type
        consequence = self._calculate_consequence(
            source=event.source_type,
            event_type=event.event_type,
            metadata=event.metadata,
            raw_payload=event.raw_payload,
        )

        # Estimate compute cost from payload complexity
        compute_cost = self._calculate_compute_cost(event.raw_payload)

        rationale = (
            f"Rule-based policy ({self._policy_version}): severity={event.severity.value}, "
            f"source={event.source_type}, event_type={event.event_type}"
        )

        return ValueAssessment(
            work_item_id=event.event_id,
            work_item_type="signal",
            urgency=urgency,
            confidence=confidence,
            consequence_of_drop=consequence,
            estimated_compute_cost=compute_cost,
            rationale=rationale,
            estimator=self._policy_version,
            policy_version="v1.0",
            deadline=event.deadline_at,
        )

    def _estimate_incident(self, incident: CoalescedIncident) -> ValueAssessment:
        """Estimate value for CoalescedIncident based on aggregated signal count and sources."""
        # Incident urgency increases with signal count
        count_factor = min(0.30, (incident.signal_count - 1) * 0.05)
        urgency = round(min(1.0, 0.60 + count_factor), 2)
        confidence = 0.90

        # Aggregated signals increase consequence of drop
        base_consequence = 0.70
        consequence = round(min(1.0, base_consequence + count_factor), 2)

        # Compute cost scales with number of coalesced signals
        compute_cost = round(1.0 + min(3.0, incident.signal_count * 0.1), 2)

        rationale = (
            f"Rule-based policy ({self._policy_version}): coalesced incident with {incident.signal_count} "
            f"signals across sources={incident.source_types}"
        )

        return ValueAssessment(
            work_item_id=incident.incident_id,
            work_item_type="incident",
            urgency=urgency,
            confidence=confidence,
            consequence_of_drop=consequence,
            estimated_compute_cost=compute_cost,
            rationale=rationale,
            estimator=self._policy_version,
            policy_version="v1.0",
        )

    def _map_severity_to_urgency(self, severity: str) -> float:
        """Map categorical severity to urgency score in [0.0, 1.0]."""
        mapping = {
            "critical": 0.90,
            "high": 0.75,
            "medium": 0.50,
            "low": 0.30,
            "info": 0.15,
        }
        return mapping.get(severity.lower(), 0.40)

    def _calculate_consequence(
        self, source: str, event_type: str, metadata: dict, raw_payload: dict
    ) -> float:
        """Evaluate consequence of drop from keyword analysis."""
        critical_keywords = {"payment", "database", "outage", "security", "crash", "failure", "exhausted", "502", "500"}
        minor_keywords = {"info", "debug", "ping", "heartbeat", "minor"}

        text = f"{source} {event_type} {json.dumps(metadata)} {json.dumps(raw_payload)}".lower()

        if any(kw in text for kw in critical_keywords):
            return 0.90
        elif any(kw in text for kw in minor_keywords):
            return 0.25
        return 0.55

    def _calculate_compute_cost(self, raw_payload: dict) -> float:
        """Calculate relative compute cost based on payload size."""
        payload_str = json.dumps(raw_payload)
        length = len(payload_str)
        # Base cost 0.5 + 0.5 per 1000 chars (max 3.0)
        return round(max(0.5, min(3.0, 0.5 + (length / 2000))), 2)
