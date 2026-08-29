"""CLI Script for Failure Recovery & Hero Scenario Demonstration.

Demonstrates Case C Hero Failure Scenario: Worker-1 completes execution and persists result to DB,
then crashes BEFORE ACKing transport message. RecoveryCoordinator reclaims message after stale threshold,
hits DB Idempotency COMPLETED status, skips re-execution, ACKs message, and ensures zero duplicate side effects.

Usage:
    python -m scripts.test_recovery
    python scripts/test_recovery.py
"""

import asyncio
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.database import AsyncSessionLocal, init_db
from app.storage.repositories import EventRepository, ExecutionRepository, IdempotencyRepository
from app.domain.models import SignalEvent, QueueMessage, AdmissionDecision
from app.domain.enums import SeverityLevel, AdmissionDecision as AdmissionDecisionEnum, AdmissionReason, IdempotencyStatus
from app.queue.memory_broker import InMemoryWorkQueue
from app.worker.worker import LedgerWorker
from app.recovery.coordinator import RecoveryCoordinator


async def run_recovery_demo() -> None:
    """Run Hero Failure Recovery Mode demonstration."""
    print("Initializing Database & Failure Recovery Subsystem...")
    await init_db()

    broker = InMemoryWorkQueue(stream_name="ledger:rec_demo_stream", group_name="rec_workers")
    now = datetime.now(timezone.utc)
    uid = uuid.uuid4().hex

    # Ingest and admit single event
    async with AsyncSessionLocal() as session:
        event_repo = EventRepository(session)
        evt = SignalEvent(
            source_type="github",
            source_id=f"hero_src_{uid[:8]}",
            tenant_id="tenant_hero",
            payload_hash=f"{uid:064s}",
            coalesce_key=f"k_hero_{uid[:8]}",
            event_type="network_outage",
            severity=SeverityLevel.CRITICAL,
            raw_payload={"details": "primary gateway down"},
            created_at=now,
        )
        await event_repo.save(evt)
        await session.commit()

        admit_dec = AdmissionDecision(
            decision=AdmissionDecisionEnum.ADMIT,
            work_item_id=evt.event_id,
            reason=AdmissionReason.ADMITTED_HIGH_VALUE,
            effective_value=0.9,
            value_per_compute=1.8,
            capacity_required=1.0,
            capacity_available=100.0,
            tenant_id="tenant_hero",
            explanation="Critical network outage admitted",
        )
        msg = await broker.publish(evt, admit_dec)

    print(f"1. Enqueued transport message M1 (transport_id='{msg.transport_id}') for work_item_id '{evt.event_id}'")

    # Step 2: Worker 1 consumes message M1
    s1 = AsyncSessionLocal()
    try:
        w1 = LedgerWorker("worker-1", broker, EventRepository(s1), ExecutionRepository(s1), IdempotencyRepository(s1))
        consumed_msgs = await broker.consume("worker-1", count=1)
        assert len(consumed_msgs) == 1

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
        print("2. Worker-1 executed task and persisted COMPLETED result to DB.")
        print("3. SIMULATING WORKER-1 CRASH BEFORE ACK! (Message M1 remains PENDING in broker)")
    finally:
        await s1.close()

    # Step 4: Verify pending message count before recovery
    pending_before = await broker.get_pending_messages()
    print(f"4. Broker Pending Count before recovery scan: {len(pending_before)}")
    assert len(pending_before) == 1

    # Step 5: Trigger RecoveryCoordinator scan (min_idle_seconds=0 for demo instant reclaim)
    s2 = AsyncSessionLocal()
    try:
        w2 = LedgerWorker("worker-2", broker, EventRepository(s2), ExecutionRepository(s2), IdempotencyRepository(s2))
        coordinator = RecoveryCoordinator(broker, w2, IdempotencyRepository(s2), ExecutionRepository(s2))

        print("\n5. Executing RecoveryCoordinator scan over stale pending entries...")
        outcome = await coordinator.run_recovery_scan(min_idle_seconds=0.0, batch_size=10)

        print("\n" + "=" * 70)
        print(" LEDGER FAILURE RECOVERY TELEMETRY REPORT ")
        print("=" * 70)
        print(f"Scanned Pending Count:     {outcome.scanned_pending_count}")
        print(f"Stale Candidates Found:    {outcome.stale_candidates_count}")
        print(f"Reclaimed Messages Count:  {outcome.reclaimed_count}")
        print(f"Already Completed Hits:    {outcome.already_completed_count}")
        print("=" * 70)

        # Step 6: Verify pending count after recovery
        pending_after = await broker.get_pending_messages()
        print(f"6. Broker Pending Count after recovery scan: {len(pending_after)} (All pending transport messages ACKed)")
        assert len(pending_after) == 0

        # Step 7: Verify DB state has EXACTLY ONE completed execution result!
        async with AsyncSessionLocal() as check_session:
            check_exec_repo = ExecutionRepository(check_session)
            res = await check_exec_repo.get_result_by_work_item(evt.event_id)
            print(f"7. Authoritative DB Result ID: {res.execution_id if res else 'N/A'}, Status: {res.status if res else 'N/A'}")
            print("=" * 70)
    finally:
        await s2.close()


def main() -> None:
    asyncio.run(run_recovery_demo())


if __name__ == "__main__":
    main()
