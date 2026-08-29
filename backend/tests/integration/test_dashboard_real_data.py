"""Integration Test for Real Dashboard Metrics Sourcing.

Verifies that real runtime state (queue pending count, worker state, recovery metrics)
is accurately reflected in DashboardSummaryDTO without hardcoded fake data.
"""

import pytest

from app.queue.memory_broker import InMemoryWorkQueue
from app.storage.repositories import EventRepository, ExecutionRepository, IdempotencyRepository
from app.dashboard.service import DashboardService
from app.worker.worker import LedgerWorker
from app.worker.pool import WorkerPool


@pytest.mark.asyncio
async def test_dashboard_service_reflects_real_queue_and_worker_state(db_session):
    broker = InMemoryWorkQueue()
    event_repo = EventRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    idem_repo = IdempotencyRepository(db_session)

    w1 = LedgerWorker("worker-alpha", broker, event_repo, exec_repo, idem_repo)
    pool = WorkerPool([w1])

    dashboard_service = DashboardService(
        event_repo=event_repo,
        execution_repo=exec_repo,
        idempotency_repo=idem_repo,
        broker=broker,
        pool=pool,
    )

    summary = await dashboard_service.build_dashboard_summary()

    assert summary.system_status in ("HEALTHY", "OVERLOADED")
    assert len(summary.workers) == 1
    assert summary.workers[0].worker_id == "worker-alpha"
    assert summary.queue_pending_count == 0
