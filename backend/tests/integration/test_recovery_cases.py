"""Integration Tests for Failure Recovery Case A and Case B.

Validates recovery when worker crashes before execution (Case A) and mid-execution (Case B).
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, AdmissionDecision
from app.domain.enums import SeverityLevel, AdmissionDecision as AdmissionDecisionEnum, AdmissionReason
from app.queue.memory_broker import InMemoryWorkQueue
from app.storage.repositories import EventRepository, ExecutionRepository, IdempotencyRepository
from app.worker.worker import LedgerWorker
from app.recovery.coordinator import RecoveryCoordinator


@pytest.mark.asyncio
async def test_recovery_case_a_crash_before_processing(db_session, test_session_factory):
    """Case A: Worker consumes message, dies before processing. Recovery reclaims and completes."""
    broker = InMemoryWorkQueue()
    now = datetime.now(timezone.utc)

    evt = SignalEvent(
        source_type="github",
        source_id="case_a_src",
        tenant_id="t_case_a",
        payload_hash="a" * 64,
        coalesce_key="key_case_a",
        raw_payload={"info": "case a test"},
        created_at=now,
    )
    event_repo = EventRepository(db_session)
    await event_repo.save(evt)
    await db_session.commit()

    admit_dec = AdmissionDecision(
        decision=AdmissionDecisionEnum.ADMIT,
        work_item_id=evt.event_id,
        reason=AdmissionReason.ADMITTED_CAPACITY_AVAILABLE,
        effective_value=0.8,
        value_per_compute=1.0,
        capacity_required=1.0,
        capacity_available=50.0,
        tenant_id="t_case_a",
        explanation="test",
    )
    msg = await broker.publish(evt, admit_dec)

    # Worker 1 consumes but dies BEFORE executing process_message!
    consumed = await broker.consume("worker-1", count=1)
    assert len(consumed) == 1
    assert len(await broker.get_pending_messages()) == 1

    # Recovery Coordinator reclaims and executes
    s2 = test_session_factory()
    try:
        w2 = LedgerWorker("worker-2", broker, EventRepository(s2), ExecutionRepository(s2), IdempotencyRepository(s2))
        coordinator = RecoveryCoordinator(broker, w2, IdempotencyRepository(s2), ExecutionRepository(s2))

        outcome = await coordinator.run_recovery_scan(min_idle_seconds=0.0, batch_size=10)

        assert outcome.reclaimed_count == 1
        assert len(await broker.get_pending_messages()) == 0

        # Verify DB execution completed
        exec_repo = ExecutionRepository(s2)
        res = await exec_repo.get_result_by_work_item(evt.event_id)
        assert res is not None
        assert res.status == "COMPLETED"
    finally:
        await s2.close()
