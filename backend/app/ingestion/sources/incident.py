"""Incident & Telemetry Source Adapter.

Converts monitoring alerts, APM telemetry, and incident feeds into SignalEvent entities.
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from app.domain.models import SignalEvent
from app.ingestion.sources.base import BaseSourceAdapter


class IncidentSourceAdapter(BaseSourceAdapter):
    """Adapter for system incident & APM telemetry alerts."""

    @property
    def source_type(self) -> str:
        return "incident"

    def can_handle(self, headers: dict[str, str], payload: dict[str, Any]) -> bool:
        """Check if request payload matches incident / telemetry schema."""
        return "incident_id" in payload or "alert_name" in payload or "severity" in payload

    def parse_raw(self, headers: dict[str, str], payload: dict[str, Any], tenant_id: str) -> SignalEvent:
        """Parse incident alert into SignalEvent."""
        incident_id = payload.get("incident_id") or payload.get("alert_id")
        if not incident_id:
            incident_id = f"inc_{hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]}"

        service_name = payload.get("service") or payload.get("system") or "global"
        alert_name = payload.get("alert_name") or payload.get("title") or "alert"
        coalesce_key = f"incident_{service_name}_{alert_name}"

        raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(raw_bytes).hexdigest()

        # Incidents have short deadlines (e.g. 15 to 30 mins) based on severity
        severity = str(payload.get("severity", "P3")).upper()
        ttl_minutes = 10 if severity in ("P0", "P1", "CRITICAL") else 30
        deadline = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

        return SignalEvent(
            source_type=self.source_type,
            source_id=str(incident_id),
            tenant_id=tenant_id,
            payload_hash=payload_hash,
            coalesce_key=coalesce_key,
            raw_payload={
                "severity": severity,
                "service": service_name,
                "alert": alert_name,
                "details": payload,
            },
            deadline_at=deadline,
        )
