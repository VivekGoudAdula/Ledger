"""Unit Tests for QueueMessage Domain Entity.

Validates serialization/deserialization contracts, schema versioning, and transport ID isolation.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import QueueMessage


def test_valid_queue_message_serialization():
    now = datetime.now(timezone.utc)
    msg = QueueMessage(
        work_item_id="item_123",
        tenant_id="tenant_a",
        effective_value=0.85,
        value_per_compute=1.70,
        admission_decision_id="DEC-001",
        enqueued_at=now,
    )

    data = msg.to_dict()
    assert data["work_item_id"] == "item_123"
    assert data["tenant_id"] == "tenant_a"
    assert data["schema_version"] == "1"
    assert data["effective_value"] == "0.85"

    reconstructed = QueueMessage.from_dict(data, transport_id="1724925000000-0")
    assert reconstructed.work_item_id == msg.work_item_id
    assert reconstructed.tenant_id == msg.tenant_id
    assert reconstructed.transport_id == "1724925000000-0"
    assert reconstructed.effective_value == 0.85


def test_invalid_schema_version_rejected():
    with pytest.raises(ValueError, match="schema_version"):
        QueueMessage(
            work_item_id="item_err",
            tenant_id="tenant_a",
            effective_value=0.5,
            value_per_compute=0.5,
            admission_decision_id="DEC-002",
            schema_version=2,  # Invalid schema version
        )


def test_naive_timestamp_rejected():
    naive_time = datetime.now()
    with pytest.raises(ValueError, match="timezone-aware"):
        QueueMessage(
            work_item_id="item_tz",
            tenant_id="tenant_a",
            effective_value=0.5,
            value_per_compute=0.5,
            admission_decision_id="DEC-003",
            enqueued_at=naive_time,
        )
