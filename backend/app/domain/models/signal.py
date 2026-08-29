"""Canonical SignalEvent Domain Entity.

Represents an immutable, source-independent canonical work item within Ledger.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from app.domain.enums import EventStatus, EventSource, SeverityLevel


@dataclass
class SignalEvent:
    """Canonical SignalEvent domain entity.

    Contains source metadata, severity classification, payload hash,
    and timezone-aware timing bounds.
    """

    source_type: str
    source_id: str
    tenant_id: str
    payload_hash: str
    coalesce_key: str
    raw_payload: dict[str, Any]
    event_type: str = "generic_event"
    severity: SeverityLevel = SeverityLevel.INFO
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deadline_at: datetime | None = None
    status: EventStatus = EventStatus.RECEIVED
    retry_count: int = 0
    coalesced_into_id: str | None = None
    coalesced_count: int = 1

    def __post_init__(self) -> None:
        """Validate canonical SignalEvent fields."""
        if not self.event_id or not isinstance(self.event_id, str) or not self.event_id.strip():
            raise ValueError("event_id must be a non-empty string")

        if not self.tenant_id or not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValueError("tenant_id must be a non-empty string")

        if not self.source_type or not isinstance(self.source_type, str) or not self.source_type.strip():
            raise ValueError("source_type must be a non-empty string")

        if not self.event_type or not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValueError("event_type must be a non-empty string")

        # Validate timezone awareness
        if self.created_at.tzinfo is None or self.created_at.tzinfo.utcoffset(self.created_at) is None:
            raise ValueError("created_at timestamp must be timezone-aware (tzinfo cannot be None)")

        if self.deadline_at is not None:
            if self.deadline_at.tzinfo is None or self.deadline_at.tzinfo.utcoffset(self.deadline_at) is None:
                raise ValueError("deadline_at timestamp must be timezone-aware (tzinfo cannot be None)")

        if isinstance(self.severity, str):
            try:
                object.__setattr__(self, "severity", SeverityLevel(self.severity.lower()))
            except ValueError:
                raise ValueError(f"Invalid severity level: {self.severity}")

    def is_expired(self, current_time: datetime | None = None) -> bool:
        """Check if the event deadline has passed."""
        if self.deadline_at is None:
            return False
        now = current_time or datetime.now(timezone.utc)
        return now > self.deadline_at

    def mark_status(self, new_status: EventStatus) -> None:
        """Update event status."""
        self.status = new_status
