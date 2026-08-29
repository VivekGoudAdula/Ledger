"""Public Status & Incident Feed Source Adapter.

Converts public status page incidents into canonical SignalEvent entities with stable event identity.
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from app.domain.models import SignalEvent
from app.domain.enums import SeverityLevel
from app.ingestion.sources.base import BaseSourceAdapter


class StatusFeedAdapter(BaseSourceAdapter):
    """Adapter converting public status feed incidents into SignalEvents."""

    @property
    def source_type(self) -> str:
        return "status_feed"

    def can_handle(self, headers: dict[str, str], payload: dict[str, Any]) -> bool:
        """Check if payload matches status feed incident schema."""
        return "incident_updates" in payload or "impact" in payload or "page" in payload

    def parse_raw(self, headers: dict[str, str], payload: dict[str, Any], tenant_id: str) -> SignalEvent:
        """Parse raw status feed incident into canonical SignalEvent."""
        incident_id = str(payload.get("id") or payload.get("incident_id") or "unknown")
        title = str(payload.get("name") or payload.get("title") or "Public Incident")
        impact = str(payload.get("impact") or payload.get("severity") or "minor").lower()

        # Severity mapping
        if impact in ("critical", "major", "p0", "p1"):
            severity = SeverityLevel.CRITICAL if impact == "critical" else SeverityLevel.HIGH
        elif impact in ("minor", "medium", "p2"):
            severity = SeverityLevel.MEDIUM
        else:
            severity = SeverityLevel.INFO

        coalesce_key = f"status_{impact}_{incident_id[:8]}"
        raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(raw_bytes).hexdigest()

        # TTL based on impact
        ttl_minutes = 15 if severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH) else 60
        deadline = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

        metadata = {
            "incident_id": incident_id,
            "impact": impact,
            "shortlink": payload.get("shortlink"),
            "status": payload.get("status"),
        }

        return SignalEvent(
            source_type=self.source_type,
            source_id=f"status_{incident_id}",
            tenant_id=tenant_id,
            payload_hash=payload_hash,
            coalesce_key=coalesce_key,
            event_type=f"status_feed_incident_{impact}",
            severity=severity,
            raw_payload=payload,
            metadata=metadata,
            deadline_at=deadline,
        )
