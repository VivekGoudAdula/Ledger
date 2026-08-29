"""Event Normalizer Service.

Routes raw payloads to registered source adapters and produces normalized SignalEvents.
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Sequence

from app.domain.models import SignalEvent
from app.ingestion.sources import BaseSourceAdapter, GitHubSourceAdapter, IncidentSourceAdapter


class EventNormalizer:
    """Normalizes raw input signals using a pluggable list of source adapters."""

    def __init__(self, adapters: Sequence[BaseSourceAdapter] | None = None) -> None:
        self._adapters: list[BaseSourceAdapter] = list(adapters) if adapters else [
            GitHubSourceAdapter(),
            IncidentSourceAdapter(),
        ]

    def register_adapter(self, adapter: BaseSourceAdapter) -> None:
        """Register a new source adapter."""
        self._adapters.append(adapter)

    def normalize(self, headers: dict[str, str], payload: dict[str, Any], tenant_id: str = "default") -> SignalEvent:
        """Find matching adapter and parse raw signal into canonical SignalEvent."""
        for adapter in self._adapters:
            if adapter.can_handle(headers, payload):
                return adapter.parse_raw(headers, payload, tenant_id)

        # Fallback generic API event parser
        raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(raw_bytes).hexdigest()
        source_id = payload.get("id") or payload.get("event_id") or payload_hash[:12]
        coalesce_key = payload.get("category") or payload.get("topic") or "generic"

        ttl = float(payload.get("ttl_seconds", 3600))
        deadline = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        return SignalEvent(
            source_type="generic_api",
            source_id=str(source_id),
            tenant_id=tenant_id,
            payload_hash=payload_hash,
            coalesce_key=f"api_{coalesce_key}",
            raw_payload=payload,
            deadline_at=deadline,
        )
