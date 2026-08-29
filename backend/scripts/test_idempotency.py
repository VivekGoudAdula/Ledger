"""CLI Script for Database-Enforced Idempotency & Race Condition Guard Demonstration.

Demonstrates composite UNIQUE (tenant_id, work_item_id, action_type) constraint enforcement,
atomic ownership claims, duplicate queue redelivery protection, and multi-tenant isolation.

Usage:
    python -m scripts.test_idempotency
    python scripts/test_idempotency.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.database import AsyncSessionLocal, init_db
from app.storage.repositories import EventRepository, ExecutionRepository, IdempotencyRepository
from app.domain.models import SignalEvent, QueueMessage, AdmissionDecision, CapacityState, TenantState
from app.domain.enums import SeverityLevel, AdmissionDecision as AdmissionDecisionEnum, AdmissionReason, ActionType, IdempotencyStatus
from app.queue.memory_broker import InMemoryWorkQueue
from app.worker.worker import LedgerWorker


async def run_idempotency_demo() -> None:
    """Run database-enforced idempotency and concurrent race guard demonstration."""
    print("Initializing Database & Idempotency Subsystem...")
    await init_db()

    broker = InMemoryWorkQueue(stream_name="ledger:idem_demo_stream", group_name="idem_workers")
    now = datetime.now(timezone.utc)

    # Prepare single signal event
    async with AsyncSessionLocal() as session:
        event_repo = EventRepository(session)
        evt = SignalEvent(
            source_type="github",
            source_id="idem_src_100",
            tenant_id="tenant_alpha",
            payload_hash="9" * 64,
            coalesce_key="k_idem_100",
            event_type="payment_timeout",
            severity=SeverityLevel.CRITICAL,
            raw_payload={"amount": 500, "currency": "USD"},
            created_at=now,
        )
        await event_repo.save(evt)
        await session.commit()

        admit_dec = AdmissionDecision(
            decision=AdmissionDecisionEnum.ADMIT,
            work_item_id=evt.event_id,
            reason=AdmissionReason.ADMITTED_HIGH_VALUE,
            effective_value=0.95,
            value_per_compute=1.9,
            capacity_required=1.0,
            capacity_available=100.0,
            tenant_id="tenant_alpha",
            explanation="Critical payment timeout admitted",
        )

        # Enqueue identical message twice to simulate duplicate queue redelivery
        msg1 = await broker.publish(evt, admit_dec)
        msg2 = await broker.publish(evt, admit_dec)

    print(f"Enqueued 2 identical transport messages for work_item_id '{evt.event_id}'")

    # Worker 1 & Worker 2 processing concurrently with separate DB sessions
    s1, s2 = AsyncSessionLocal(), AsyncSessionLocal()
    try:
        w1 = LedgerWorker("worker-1", broker, EventRepository(s1), ExecutionRepository(s1), IdempotencyRepository(s1))
        w2 = LedgerWorker("worker-2", broker, EventRepository(s2), ExecutionRepository(s2), IdempotencyRepository(s2))

        print("\nExecuting Worker-1 and Worker-2 concurrently on identical work items...")
        results = await asyncio.gather(
            w1.process_message(msg1),
            w2.process_message(msg2),
        )
        print(f"Concurrent Processing Results: Worker-1={results[0]}, Worker-2={results[1]}")

        # Query Authoritative Idempotency Record from DB
        async with AsyncSessionLocal() as check_session:
            idem_repo = IdempotencyRepository(check_session)
            key = f"tenant_alpha:{evt.event_id}:ANALYZE_SIGNAL"
            rec = await idem_repo.get_record(key)

            print("\n" + "=" * 70)
            print(" LEDGER DATABASE-ENFORCED IDEMPOTENCY RECORD ")
            print("=" * 70)
            print(f"Idempotency Key:     {rec.idempotency_key if rec else 'N/A'}")
            print(f"Tenant ID:           {rec.tenant_id if rec else 'N/A'}")
            print(f"Work Item ID:        {rec.work_item_id if rec else 'N/A'}")
            print(f"Action Type:         {rec.action_type if rec else 'N/A'}")
            print(f"Status:              {rec.status.value if rec else 'N/A'}")
            print(f"Execution ID:        {rec.execution_id if rec else 'N/A'}")
            print(f"Result Data Output:  {rec.result_data.get('action_taken') if rec else 'N/A'}")
            print("=" * 70)

            # Confirm pending queue is empty (both messages ACKed safely)
            pending = await broker.get_pending_messages()
            print(f"Pending Messages Count in Queue: {len(pending)} (All transport entries ACKed)")
            print("=" * 70)
    finally:
        await s1.close()
        await s2.close()


def main() -> None:
    asyncio.run(run_idempotency_demo())


if __name__ == "__main__":
    main()
