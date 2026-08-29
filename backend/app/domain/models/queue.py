"""Queue Domain Models.

Defines QueueMessage (versioned queue payload) and QueueMetrics telemetry dataclasses.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class QueueMessage:
    """Versioned application queue message transport payload."""

    work_item_id: str
    tenant_id: str
    effective_value: float
    value_per_compute: float
    admission_decision_id: str
    schema_version: int = 1
    transport_id: str | None = None  # Broker transport ID (e.g. Redis Stream ID '1724925000000-0')
    message_id: str = field(default_factory=lambda: f"MSG-{uuid.uuid4().hex[:8]}")
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate message fields and schema version."""
        if not self.work_item_id or not isinstance(self.work_item_id, str):
            raise ValueError("QueueMessage work_item_id must be a non-empty string.")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValueError("QueueMessage tenant_id must be a non-empty string.")
        if self.schema_version != 1:
            raise ValueError(f"Unsupported QueueMessage schema_version: {self.schema_version}")
        if self.enqueued_at and self.enqueued_at.tzinfo is None:
            raise ValueError("enqueued_at timestamp must be timezone-aware.")

    def to_dict(self) -> dict[str, str]:
        """Serialize payload to string dictionary for broker transport."""
        return {
            "message_id": self.message_id,
            "work_item_id": self.work_item_id,
            "tenant_id": self.tenant_id,
            "schema_version": str(self.schema_version),
            "effective_value": str(self.effective_value),
            "value_per_compute": str(self.value_per_compute),
            "admission_decision_id": self.admission_decision_id,
            "enqueued_at": self.enqueued_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], transport_id: str | None = None) -> "QueueMessage":
        """Deserialize raw broker string payload into typed QueueMessage domain entity."""
        schema_ver = int(data.get("schema_version", 1))
        if schema_ver != 1:
            raise ValueError(f"Incompatible queue message schema_version: {schema_ver}")

        enqueued_at_raw = data["enqueued_at"]
        dt = datetime.fromisoformat(enqueued_at_raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return cls(
            message_id=data["message_id"],
            work_item_id=data["work_item_id"],
            tenant_id=data["tenant_id"],
            effective_value=float(data["effective_value"]),
            value_per_compute=float(data["value_per_compute"]),
            admission_decision_id=data["admission_decision_id"],
            schema_version=schema_ver,
            transport_id=transport_id or data.get("transport_id"),
            enqueued_at=dt,
        )


@dataclass
class QueueMetrics:
    """Queue depth and consumer group telemetry metrics."""

    stream_length: int
    pending_count: int
    consumer_count: int
    stream_name: str
    consumer_group: str
