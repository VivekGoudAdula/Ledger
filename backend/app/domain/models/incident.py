"""CoalescedIncident Domain Entity.

Represents a coalesced incident / work item grouping multiple related SignalEvents.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class CoalescedIncident:
    """Canonical Coalesced Incident domain model.

    Groups multiple source SignalEvent entities representing the same underlying condition
    or incident while maintaining full auditability and traceability to original signals.
    """

    tenant_id: str
    coalesce_key: str
    representative_title: str
    source_types: list[str] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)
    signal_count: int = 1
    coalescing_method: str = "deterministic_fingerprint"
    incident_id: str = field(default_factory=lambda: f"INC-{str(uuid.uuid4())[:8]}")
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate CoalescedIncident fields and timezone awareness."""
        if not self.incident_id or not isinstance(self.incident_id, str):
            raise ValueError("incident_id must be a non-empty string")

        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValueError("tenant_id must be a non-empty string")

        if not self.coalesce_key or not isinstance(self.coalesce_key, str):
            raise ValueError("coalesce_key must be a non-empty string")

        # Validate timezone awareness
        for field_name, dt in [("first_seen", self.first_seen), ("last_seen", self.last_seen), ("created_at", self.created_at)]:
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                raise ValueError(f"{field_name} timestamp must be timezone-aware (tzinfo cannot be None)")

    def add_signal(self, event_id: str, source_type: str, event_timestamp: datetime) -> None:
        """Link a new signal event to this coalesced incident."""
        if event_id not in self.event_ids:
            self.event_ids.append(event_id)
            self.signal_count += 1

        if source_type not in self.source_types:
            self.source_types.append(source_type)

        if event_timestamp > self.last_seen:
            self.last_seen = event_timestamp
        if event_timestamp < self.first_seen:
            self.first_seen = event_timestamp
