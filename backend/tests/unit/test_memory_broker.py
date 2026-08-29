"""Unit Tests for InMemoryWorkQueue Broker Adapter.

Validates publish guards, consumer group reads, pending entry tracking, and ACKs.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import (
    SignalEvent,
    AdmissionDecision,
    CapacityState,
)
from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum, AdmissionReason
from app.queue.memory_broker import InMemoryWorkQueue


@pytest.mark.asyncio
async def test_memory_broker_publish_admit_success():
    broker = InMemoryWorkQueue()
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        raw_payload={"test": "data"},
        created_at=now,
    )

    admit_decision = AdmissionDecision(
        decision=AdmissionDecisionEnum.ADMIT,
        work_item_id=event.event_id,
        reason=AdmissionReason.ADMITTED_CAPACITY_AVAILABLE,
        effective_value=0.8,
        value_per_compute=1.0,
        capacity_required=1.0,
        capacity_available=50.0,
        tenant_id="t1",
        explanation="test",
        evaluated_at=now,
    )

    msg = await broker.publish(event, admit_decision)
    assert msg.work_item_id == event.event_id
    assert msg.transport_id is not None

    metrics = await broker.get_metrics()
    assert metrics.stream_length == 1


@pytest.mark.asyncio
async def test_memory_broker_publish_defer_or_shed_rejected():
    broker = InMemoryWorkQueue()
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="2",
        tenant_id="t1",
        payload_hash="b" * 64,
        coalesce_key="k2",
        raw_payload={"test": "data"},
    )

    defer_decision = AdmissionDecision(
        decision=AdmissionDecisionEnum.DEFER,
        work_item_id=event.event_id,
        reason=AdmissionReason.DEFERRED_CAPACITY_EXHAUSTED,
        effective_value=0.5,
        value_per_compute=0.5,
        capacity_required=10.0,
        capacity_available=0.0,
        tenant_id="t1",
        explanation="test",
        evaluated_at=now,
    )

    with pytest.raises(ValueError, match="Only ADMIT decisions are queueable"):
        await broker.publish(event, defer_decision)


@pytest.mark.asyncio
async def test_memory_broker_consume_ack_lifecycle():
    broker = InMemoryWorkQueue()
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="3",
        tenant_id="t1",
        payload_hash="c" * 64,
        coalesce_key="k3",
        raw_payload={"test": "data"},
    )
    decision = AdmissionDecision(
        decision=AdmissionDecisionEnum.ADMIT,
        work_item_id=event.event_id,
        reason=AdmissionReason.ADMITTED_CAPACITY_AVAILABLE,
        effective_value=0.9,
        value_per_compute=1.0,
        capacity_required=1.0,
        capacity_available=50.0,
        tenant_id="t1",
        explanation="test",
        evaluated_at=now,
    )

    await broker.publish(event, decision)

    # Consume
    consumed = await broker.consume(consumer_name="worker-1", count=1)
    assert len(consumed) == 1
    t_id = consumed[0].transport_id

    # Pending count before ACK
    pending = await broker.get_pending_messages()
    assert len(pending) == 1

    # Acknowledge
    ack_res = await broker.acknowledge(t_id)
    assert ack_res is True

    # Pending count after ACK
    pending_after = await broker.get_pending_messages()
    assert len(pending_after) == 0
