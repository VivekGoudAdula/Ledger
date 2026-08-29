"""CLI Script for Real Signal Pipeline End-to-End Smoke Test.

Contacts live public GitHub and Status Feed endpoints (if online) and routes live items through the
complete Ledger pipeline: Adapter -> SignalEvent -> Ingestion -> Valuation -> Admission -> Queue -> Worker Execution -> Idempotency -> Result Persistence.

Usage:
    python -m scripts.run_pipeline_smoke
    python scripts/run_pipeline_smoke.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.database import AsyncSessionLocal, init_db
from app.storage.repositories import EventRepository, IncidentRepository, ValuationRepository, ExecutionRepository, IdempotencyRepository
from app.coalescing.service import CoalescingService
from app.ingestion.service import IngestionService
from app.ingestion.polling import SourcePollingService
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.admission.controller import AdmissionController
from app.domain.models import CapacityState, TenantState
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService
from app.worker.worker import LedgerWorker
from app.worker.pool import WorkerPool


async def run_pipeline_smoke_demo() -> None:
    """Run real signal pipeline end-to-end smoke test."""
    print("Initializing Database & Ledger Real Signal Pipeline Subsystem...")
    await init_db()

    broker = InMemoryWorkQueue(stream_name="ledger:smoke_stream", group_name="smoke_workers")
    valuation_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), mode="rule_based")
    admission_controller = AdmissionController()
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="tenant_github", quota=50.0)

    async with AsyncSessionLocal() as session:
        event_repo = EventRepository(session)
        incident_repo = IncidentRepository(session)
        coalescing_service = CoalescingService(incident_repo)
        ingestion_service = IngestionService(event_repo, coalescing_service)
        publisher_service = QueuePublisherService(broker, event_repo)

        polling_service = SourcePollingService(ingestion_service=ingestion_service, broker=broker)

        print("\n1. Polling Live GitHub API for Public Events...")
        gh_events = await polling_service.poll_github(tenant_id="tenant_github", limit=5)
        print(f"   Received and ingested {len(gh_events)} live GitHub SignalEvents.")

        print("\n2. Polling Live Public Status Feed for Incidents...")
        status_events = await polling_service.poll_status_feed(tenant_id="tenant_status")
        print(f"   Received and ingested {len(status_events)} live Status Feed SignalEvents.")

        all_ingested = gh_events + status_events
        print(f"\n3. Total Ingested Events: {len(all_ingested)}")

        now = datetime.now(timezone.utc)
        admitted_ids = []
        for evt in all_ingested:
            assessment = await valuation_service.assess_work_item(evt)
            decision = admission_controller.evaluate_admission(evt, assessment, capacity, tenant, evaluation_time=now)
            status, msg = await publisher_service.handle_admission_decision(evt, decision)
            if msg:
                admitted_ids.append(evt.event_id)

        await session.commit()
        print(f"4. Valued & Admitted {len(admitted_ids)} work items into transport stream.")

    # Execute Multi-Worker Pool over admitted work items
    s1, s2 = AsyncSessionLocal(), AsyncSessionLocal()
    try:
        workers = [
            LedgerWorker("worker-1", broker, EventRepository(s1), ExecutionRepository(s1), IdempotencyRepository(s1)),
            LedgerWorker("worker-2", broker, EventRepository(s2), ExecutionRepository(s2), IdempotencyRepository(s2)),
        ]
        pool = WorkerPool(workers)

        print("\n5. Executing Worker Pool processing over transport queue stream...")
        processed = await pool.run_step()
        print(f"   Worker Pool processed {processed} tasks successfully.")

        print("\n" + "=" * 70)
        print(" LEDGER END-TO-END PIPELINE SMOKE TEST SUMMARY ")
        print("=" * 70)
        print(f"Live GitHub Signals:     {len(gh_events)}")
        print(f"Live Status Feed Signals:{len(status_events)}")
        print(f"Admitted & Enqueued:    {len(admitted_ids)}")
        print(f"Worker Processed Count:  {processed}")
        print("=" * 70)
    finally:
        await s1.close()
        await s2.close()


def main() -> None:
    asyncio.run(run_pipeline_smoke_demo())


if __name__ == "__main__":
    main()
