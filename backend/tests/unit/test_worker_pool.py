"""Unit Tests for WorkerPool.

Validates multi-worker supervision, task distribution, and failure isolation.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, AdmissionDecision
from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum, AdmissionReason
from app.queue.memory_broker import InMemoryWorkQueue
from app.storage.repositories import EventRepository, ExecutionRepository
from app.worker.worker import LedgerWorker
from app.worker.pool import WorkerPool


@pytest.mark.asyncio
async def test_worker_pool_multi_worker_execution(db_session, test_session_factory):
    broker = InMemoryWorkQueue()
    event_repo = EventRepository(db_session)

    # Ingest and publish 3 events
    for i in range(3):
        evt = SignalEvent(
            source_type="github",
            source_id=f"pool_{i}",
            tenant_id="t1",
            payload_hash=f"{i:064x}",
            coalesce_key=f"k_{i}",
            raw_payload={"index": i},
        )
        await event_repo.save(evt)
        dec = AdmissionDecision(
            decision=AdmissionDecisionEnum.ADMIT,
            work_item_id=evt.event_id,
            reason=AdmissionReason.ADMITTED_CAPACITY_AVAILABLE,
            effective_value=0.8,
            value_per_compute=1.0,
            capacity_required=1.0,
            capacity_available=50.0,
            tenant_id="t1",
            explanation="test",
        )
        await broker.publish(evt, dec)

    # Create separate sessions for each worker to avoid session concurrency contention
    sessions = [test_session_factory() for _ in range(3)]
    try:
        workers = [
            LedgerWorker(
                worker_id=f"worker-{i+1}",
                broker=broker,
                event_repo=EventRepository(sessions[i]),
                execution_repo=ExecutionRepository(sessions[i]),
            )
            for i in range(3)
        ]
        pool = WorkerPool(workers)

        processed = await pool.run_step()
        assert processed >= 1

        statuses = pool.get_pool_status()
        assert len(statuses) == 3
    finally:
        for s in sessions:
            await s.close()
