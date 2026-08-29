"""Concurrency Reliability Tests for Worker Claim Races.

Simulates two concurrent workers attempting to execute the exact same task simultaneously.
Verifies that database composite unique constraint enforces single execution safety.
"""

import asyncio
from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, QueueMessage
from app.queue.memory_broker import InMemoryWorkQueue
from app.storage.repositories import EventRepository, ExecutionRepository, IdempotencyRepository
from app.worker.worker import LedgerWorker


@pytest.mark.asyncio
async def test_concurrent_worker_claim_race_safety(db_session, test_session_factory):
    broker = InMemoryWorkQueue()
    now = datetime.now(timezone.utc)

    event_repo = EventRepository(db_session)

    evt = SignalEvent(
        source_type="test",
        source_id="race_100",
        tenant_id="tenant_race",
        payload_hash="sha256_race_100",
        coalesce_key="key_race_100",
        raw_payload={"id": "race_100"},
        created_at=now,
    )
    saved_evt = await event_repo.save(evt)
    await db_session.commit()

    msg = QueueMessage(
        work_item_id=saved_evt.event_id,
        tenant_id="tenant_race",
        effective_value=0.95,
        value_per_compute=2.0,
        admission_decision_id="ADM-race-100",
    )
    broker._messages.append(msg)

    s1, s2 = test_session_factory(), test_session_factory()
    try:
        w1 = LedgerWorker("worker-race-1", broker, EventRepository(s1), ExecutionRepository(s1), IdempotencyRepository(s1))
        w2 = LedgerWorker("worker-race-2", broker, EventRepository(s2), ExecutionRepository(s2), IdempotencyRepository(s2))

        # Execute concurrent worker steps on separate DB sessions
        r1, r2 = await asyncio.gather(
            w1.process_message(msg),
            w2.process_message(msg),
        )

        # Exactly ONE worker executes (True), while the duplicate worker skips execution (False)
        assert (r1 is True and r2 is False) or (r1 is False and r2 is True)

        exec_repo = ExecutionRepository(s1)
        res = await exec_repo.get_result_by_work_item(saved_evt.event_id)
        assert res is not None
        assert res.status == "COMPLETED"
    finally:
        await s1.close()
        await s2.close()
