"""CLI Script for Multi-Worker Pool Execution & Reliability Demonstration.

Demonstrates consuming admitted work items from queue, creating execution checkpoints,
executing deterministic task analysis, persisting results, idempotency checks, and ACKs.

Usage:
    python -m scripts.run_worker_pool
    python scripts/run_worker_pool.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.database import AsyncSessionLocal, init_db
from app.storage.repositories import EventRepository, ExecutionRepository
from app.domain.models import SignalEvent, CapacityState, TenantState
from app.domain.enums import SeverityLevel
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.admission.controller import AdmissionController
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService
from app.worker.worker import LedgerWorker
from app.worker.pool import WorkerPool


async def run_worker_demo() -> None:
    """Run multi-worker pool execution demonstration."""
    print("Initializing Database & Worker Execution Subsystem...")
    await init_db()

    broker = InMemoryWorkQueue(stream_name="ledger:worker_demo_stream", group_name="demo_workers")
    valuation_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), mode="rule_based")
    admission_controller = AdmissionController()

    now = datetime.now(timezone.utc)
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="worker_demo_tenant", quota=50.0)

    print("Ingesting & Enqueuing 10 Work Items...")

    async with AsyncSessionLocal() as init_session:
        event_repo = EventRepository(init_session)
        publisher_service = QueuePublisherService(broker=broker, event_repo=event_repo)

        enqueued_ids = []
        for i in range(10):
            sev = SeverityLevel.CRITICAL if i < 3 else (SeverityLevel.MEDIUM if i < 7 else SeverityLevel.INFO)
            evt = SignalEvent(
                source_type="github",
                source_id=f"wrk_src_{i}",
                tenant_id="worker_demo_tenant",
                payload_hash=f"f{i:063x}",
                coalesce_key=f"wrk_key_{i}",
                event_type="database_outage" if i < 3 else "routine_log",
                severity=sev,
                raw_payload={"task_id": i, "details": "demo task payload"},
                created_at=now,
            )
            await event_repo.save(evt)
            assessment = await valuation_service.assess_work_item(evt)
            decision = admission_controller.evaluate_admission(evt, assessment, capacity, tenant, evaluation_time=now)
            status, msg = await publisher_service.handle_admission_decision(evt, decision)
            if msg:
                enqueued_ids.append(evt.event_id)

        await init_session.commit()
        print(f"Enqueued {len(enqueued_ids)} ADMITTED work items into transport stream.")

    # Create Worker Pool with separate DB sessions per worker
    worker_sessions = [AsyncSessionLocal() for _ in range(3)]
    try:
        workers = [
            LedgerWorker(
                worker_id=f"worker-{w_idx+1}",
                broker=broker,
                event_repo=EventRepository(worker_sessions[w_idx]),
                execution_repo=ExecutionRepository(worker_sessions[w_idx]),
            )
            for w_idx in range(3)
        ]
        pool = WorkerPool(workers)

        print("\nExecuting Worker Pool Processing Step...")
        processed_count = await pool.run_step()
        print(f"Worker Pool processed {processed_count} tasks in step.")

        # Telemetry Summary
        print("\n" + "=" * 70)
        print(" LEDGER WORKER POOL TELEMETRY STATUS ")
        print("=" * 70)
        for status in pool.get_pool_status():
            print(f"Worker ID: {status.worker_id:<12} | Status: {status.state:<8} | Completed: {status.tasks_completed:<3} | Failed: {status.tasks_failed:<3}")
        print("=" * 70)

        # Idempotency Check Demonstration
        print("\nDemonstrating Idempotency Protection...")
        first_id = enqueued_ids[0]
        async with AsyncSessionLocal() as check_session:
            check_exec_repo = ExecutionRepository(check_session)
            result = await check_exec_repo.get_result_by_work_item(first_id)
            print(f"Work Item ID:        {first_id}")
            print(f"Execution Result ID: {result.execution_id if result else 'N/A'}")
            print(f"Execution Status:    {result.status if result else 'N/A'}")
            print(f"Output Data Summary: {result.output_data.get('action_taken') if result else 'N/A'}")
            print("=" * 70)
    finally:
        for s in worker_sessions:
            await s.close()


def main() -> None:
    asyncio.run(run_worker_demo())


if __name__ == "__main__":
    main()
