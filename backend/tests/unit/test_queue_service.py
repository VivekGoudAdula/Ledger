"""Unit Tests for QueuePublisherService.

Validates routing of ADMIT decisions to the broker and non-enqueuing of DEFER and SHED.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, AdmissionDecision
from app.domain.enums import EventStatus, AdmissionDecision as AdmissionDecisionEnum, AdmissionReason
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService


@pytest.mark.asyncio
async def test_publisher_service_admit_enqueues():
    broker = InMemoryWorkQueue()
    service = QueuePublisherService(broker=broker)
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        raw_payload={"test": "data"},
    )
    decision = AdmissionDecision(
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

    status, msg = await service.handle_admission_decision(event, decision)
    assert status == EventStatus.QUEUED
    assert msg is not None
    assert msg.work_item_id == event.event_id


@pytest.mark.asyncio
async def test_publisher_service_defer_does_not_enqueue():
    broker = InMemoryWorkQueue()
    service = QueuePublisherService(broker=broker)
    now = datetime.now(timezone.utc)

    event = SignalEvent(
        source_type="github",
        source_id="2",
        tenant_id="t1",
        payload_hash="b" * 64,
        coalesce_key="k2",
        raw_payload={"test": "data"},
    )
    decision = AdmissionDecision(
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

    status, msg = await service.handle_admission_decision(event, decision)
    assert status == EventStatus.DEFERRED
    assert msg is None

    metrics = await broker.get_metrics()
    assert metrics.stream_length == 0


@pytest.mark.asyncio
async def test_publisher_service_shed_does_not_enqueue():
    broker = InMemoryWorkQueue()
    service = QueuePublisherService(broker=broker)
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
        decision=AdmissionDecisionEnum.SHED,
        work_item_id=event.event_id,
        reason=AdmissionReason.SHED_LOW_VALUE_DURING_OVERLOAD,
        effective_value=0.05,
        value_per_compute=0.05,
        capacity_required=1.0,
        capacity_available=0.0,
        tenant_id="t1",
        explanation="test",
        evaluated_at=now,
    )

    status, msg = await service.handle_admission_decision(event, decision)
    assert status == EventStatus.SHED
    assert msg is None

    metrics = await broker.get_metrics()
    assert metrics.stream_length == 0
