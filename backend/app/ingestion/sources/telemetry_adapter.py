"""Ledger Application Telemetry Source Adapter.

Instruments running application metrics (queue depth, worker failures, recovery count) and
converts anomalous telemetry conditions into canonical SignalEvent entities with feedback-loop protection.
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from app.domain.models import SignalEvent, QueueMetrics
from app.domain.enums import SeverityLevel, EventSource
from app.ingestion.sources.base import BaseSourceAdapter


class LedgerTelemetryAdapter(BaseSourceAdapter):
    """Adapter converting Ledger runtime telemetry anomalies into SignalEvents."""

    def __init__(self, cooldown_seconds: float = 300.0) -> None:
        self._cooldown = cooldown_seconds
        self._last_emitted: dict[str, datetime] = {}

    @property
    def source_type(self) -> str:
        return EventSource.TELEMETRY.value

    def can_handle(self, headers: dict[str, str], payload: dict[str, Any]) -> bool:
        """Check if request payload represents telemetry metrics."""
        return "metric_name" in payload or "queue_depth" in payload or "pending_count" in payload

    def evaluate_metrics(self, metrics: QueueMetrics, tenant_id: str = "tenant_system") -> SignalEvent | None:
        """Evaluate queue metrics against operational thresholds and return SignalEvent if anomalous."""
        now = datetime.now(timezone.utc)

        # High pending queue backlog condition (> 50 pending items)
        if metrics.pending_count > 50:
            key = "telemetry_high_pending_backlog"
            last_time = self._last_emitted.get(key)
            if not last_time or (now - last_time).total_seconds() >= self._cooldown:
                self._last_emitted[key] = now
                payload = {
                    "metric_name": "high_pending_backlog",
                    "observed_value": metrics.pending_count,
                    "threshold": 50,
                    "stream_name": metrics.stream_name,
                }
                return self.parse_raw({}, payload, tenant_id)

        return None

    def parse_raw(self, headers: dict[str, str], payload: dict[str, Any], tenant_id: str) -> SignalEvent:
        """Parse raw telemetry payload into canonical SignalEvent."""
        metric_name = str(payload.get("metric_name") or "system_anomaly")
        observed = payload.get("observed_value", 0)

        severity = SeverityLevel.CRITICAL if observed > 100 else SeverityLevel.HIGH
        coalesce_key = f"telemetry_{metric_name}"
        raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(raw_bytes).hexdigest()
        deadline = datetime.now(timezone.utc) + timedelta(minutes=15)

        return SignalEvent(
            source_type=self.source_type,
            source_id=f"telem_{metric_name}_{payload_hash[:8]}",
            tenant_id=tenant_id,
            payload_hash=payload_hash,
            coalesce_key=coalesce_key,
            event_type=f"telemetry_anomaly_{metric_name}",
            severity=severity,
            raw_payload=payload,
            metadata={"observed_value": observed, "threshold": payload.get("threshold", 0)},
            deadline_at=deadline,
        )
