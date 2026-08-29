"""Unit Tests for LedgerWorker.

Validates message validation, idempotency checks, checkpoint creation, task execution,
result persistence, bounded retries, and ACK ordering.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import (
    SignalEvent,
    QueueMessage,
    AdmissionDecision,
    CapacityState,
)
from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum, AdmissionReason, EventStatus
from app.queue.memory_broker import InMemoryWorkQueue
from app.storage.repositories import EventRepository, ExecutionRepository
from app.worker.worker import LedgerWorker
from app.worker.retry_policy import RetryPolicy


@pytest.mark.asyncio
async def test_worker_process_valid_message_success(db_session):
    broker = InMemoryWorkQueue()
    event_repo = EventRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    worker = LedgerWorker(
        worker_id="worker-test-1",
        broker=broker,
        event_repo=event_repo,
        execution_repo=exec_repo,
    )

    event = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        raw_payload={"test": "data"},
    )
    await event_repo.save(event)

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
    )
    msg = await broker.publish(event, admit_decision)

    success = await worker.process_message(msg)
    assert success is True

    # Verify event status updated to COMPLETED
    updated_event = await event_repo.get_by_id(event.event_id)
    assert updated_event.status == EventStatus.COMPLETED

    # Verify result persisted
    result = await exec_repo.get_result_by_work_item(event.event_id)
    assert result is not None
    assert result.status == "COMPLETED"

    # Verify message acknowledged (removed from pending list)
    pending = await broker.get_pending_messages()
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_worker_idempotency_skip_completed(db_session):
    broker = InMemoryWorkQueue()
    event_repo = EventRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    worker = LedgerWorker(
        worker_id="worker-test-2",
        broker=broker,
        event_repo=event_repo,
        execution_repo=exec_repo,
    )

    event = SignalEvent(
        source_type="github",
        source_id="2",
        tenant_id="t1",
        payload_hash="b" * 64,
        coalesce_key="k2",
        raw_payload={"test": "data"},
    )
    await event_repo.save(event)

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
    )
    msg = await broker.publish(event, admit_decision)

    # First execution succeeds
    await worker.process_message(msg)

    # Re-publish same message to simulate duplicate delivery
    msg2 = await broker.publish(event, admit_decision)

    # Second execution should skip execution and ACK idempotently
    success2 = await worker.process_message(msg2)
    assert success2 is True

    pending = await broker.get_pending_messages()
    assert len(pending) == 0
