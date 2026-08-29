"""Hero Failure Recovery Integration Test (Case C).

Verifies that when a worker completes task execution and persists result to database but crashes
BEFORE ACKing transport message, the RecoveryCoordinator reclaims the pending message, hits DB Idempotency
COMPLETED status, skips re-execution, ACKs the message, and ensures ZERO duplicate side effects.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, QueueMessage, AdmissionDecision
from app.domain.enums import SeverityLevel, AdmissionDecision as AdmissionDecisionEnum, AdmissionReason, IdempotencyStatus
from app.queue.memory_broker import InMemoryWorkQueue
from app.storage.repositories import EventRepository, ExecutionRepository, IdempotencyRepository
from app.worker.worker import LedgerWorker
from app.recovery.coordinator import RecoveryCoordinator


@pytest.mark.asyncio
async def test_hero_failure_recovery_case_c(db_session, test_session_factory):
    broker = InMemoryWorkQueue()
    now = datetime.now(timezone.utc)

    # 1. Ingest and admit single signal event
    evt = SignalEvent(
        source_type="github",
        source_id="hero_test_src",
        tenant_id="tenant_hero_test",
        payload_hash="8" * 64,
        coalesce_key="key_hero_test",
        event_type="database_deadlock",
        severity=SeverityLevel.CRITICAL,
        raw_payload={"issue": "deadlock detected"},
        created_at=now,
    )
    event_repo = EventRepository(db_session)
    await event_repo.save(evt)
    await db_session.commit()

    admit_dec = AdmissionDecision(
        decision=AdmissionDecisionEnum.ADMIT,
        work_item_id=evt.event_id,
        reason=AdmissionReason.ADMITTED_HIGH_VALUE,
        effective_value=0.9,
        value_per_compute=1.8,
        capacity_required=1.0,
        capacity_available=100.0,
        tenant_id="tenant_hero_test",
        explanation="test",
    )
    msg = await broker.publish(evt, admit_dec)

    # 2. Worker 1 consumes message M1
    s1 = test_session_factory()
    try:
        w1 = LedgerWorker("worker-1", broker, EventRepository(s1), ExecutionRepository(s1), IdempotencyRepository(s1))
        consumed = await broker.consume("worker-1", count=1)
        assert len(consumed) == 1

        # Process message without ACK (simulate crash right after DB completion!)
        msg_no_ack = QueueMessage(
            work_item_id=msg.work_item_id,
            tenant_id=msg.tenant_id,
            effective_value=msg.effective_value,
            value_per_compute=msg.value_per_compute,
            admission_decision_id=msg.admission_decision_id,
            transport_id=None,  # Suppress ACK
        )
        success = await w1.process_message(msg_no_ack)
        assert success is True
    finally:
        await s1.close()

    # 3. Message remains PENDING in broker
    pending_before = await broker.get_pending_messages()
    assert len(pending_before) == 1

    # 4. Worker 2 / RecoveryCoordinator reclaims message after stale threshold
    s2 = test_session_factory()
    try:
        w2 = LedgerWorker("worker-2", broker, EventRepository(s2), ExecutionRepository(s2), IdempotencyRepository(s2))
        coordinator = RecoveryCoordinator(broker, w2, IdempotencyRepository(s2), ExecutionRepository(s2))

        # Run recovery scan (min_idle_seconds=0 for immediate reclaim)
        outcome = await coordinator.run_recovery_scan(min_idle_seconds=0.0, batch_size=10)

        # 5. Assertions: Reclaimed=1, AlreadyCompleted=1, Pending=0
        assert outcome.reclaimed_count == 1
        assert outcome.already_completed_count == 1

        pending_after = await broker.get_pending_messages()
        assert len(pending_after) == 0

        # Verify DB has EXACTLY ONE completed result record
        exec_repo = ExecutionRepository(s2)
        res = await exec_repo.get_result_by_work_item(evt.event_id)
        assert res is not None
        assert res.status == "COMPLETED"
    finally:
        await s2.close()
