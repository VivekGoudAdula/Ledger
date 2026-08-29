"""CLI Script for Queue Transport & Worker Consumer Group Demonstration.

Demonstrates publishing admitted work items, consumer group reads, message acknowledgment,
pending entry tracking, and telemetry depth metrics.

Usage:
    python -m scripts.test_queue
    python scripts/test_queue.py
"""

import asyncio
import sys
from pathlibPath = Path if (Path := None) else None
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.models import SignalEvent, CapacityState, TenantState
from app.domain.enums import SeverityLevel, EventStatus
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.admission.controller import AdmissionController
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService


async def run_queue_demo() -> None:
    """Run queue publishing and consumer group workflow demonstration."""
    print("Initializing Ledger Work Queue Subsystem...")

    broker = InMemoryWorkQueue(stream_name="ledger:demo_stream", group_name="demo_workers")
    publisher_service = QueuePublisherService(broker=broker)
    valuation_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), mode="rule_based")
    admission_controller = AdmissionController()

    now = datetime.now(timezone.utc)
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="demo_tenant", quota=50.0)

    print("Ingesting, Valuing, and Evaluating 10 work items...")

    work_items = []
    for i in range(10):
        sev = SeverityLevel.CRITICAL if i < 3 else (SeverityLevel.MEDIUM if i < 7 else SeverityLevel.INFO)
        evt = SignalEvent(
            source_type="github",
            source_id=f"queue_src_{i}",
            tenant_id="demo_tenant",
            payload_hash=f"{i:064x}",
            coalesce_key=f"q_key_{i}",
            event_type="payment_alert" if i < 3 else "routine_sync",
            severity=sev,
            raw_payload={"task_id": i},
            created_at=now,
        )

        assessment = await valuation_service.assess_work_item(evt)
        decision = admission_controller.evaluate_admission(evt, assessment, capacity, tenant, evaluation_time=now)
        status, msg = await publisher_service.handle_admission_decision(evt, decision)
        work_items.append((evt, decision, status, msg))

    # Print Publishing Results
    print("\n" + "=" * 90)
    print(f"{'WORK ITEM ID':<38} | {'SEVERITY':<8} | {'DECISION':<8} | {'QUEUE STATUS':<10} | {'TRANSPORT ID'}")
    print("=" * 90)
    for evt, dec, st, msg in work_items:
        t_id = msg.transport_id if msg else "N/A (Not Enqueued)"
        print(f"{evt.event_id:<38} | {evt.severity.value:<8} | {dec.decision.value:<8} | {st.value:<10} | {t_id}")
    print("=" * 90)

    # Worker Consumption Simulation
    print("\nSimulating Worker-1 consuming messages from 'demo_workers' group...")
    consumed = await broker.consume(consumer_name="worker-1", count=5)
    print(f"Worker-1 consumed {len(consumed)} messages into PROCESSING state.")

    # Inspect Pending Messages before ACK
    pending = await broker.get_pending_messages()
    print(f"Pending (Unacknowledged) Messages Count: {len(pending)}")

    # Acknowledge 3 messages
    print("\nWorker-1 processing and ACKing 3 messages...")
    for msg in consumed[:3]:
        await broker.acknowledge(msg.transport_id)
        print(f"Acknowledged transport_id '{msg.transport_id}' for work item '{msg.work_item_id}'")

    # Metrics Summary
    metrics = await broker.get_metrics()
    print("\n" + "=" * 60)
    print(" LEDGER QUEUE TELEMETRY METRICS SUMMARY ")
    print("=" * 60)
    print(f"Stream Name:             {metrics.stream_name}")
    print(f"Consumer Group:          {metrics.consumer_group}")
    print(f"Active Stream Length:    {metrics.stream_length}")
    print(f"Pending Messages Count:  {metrics.pending_count}")
    print(f"Active Consumer Count:   {metrics.consumer_count}")
    print("=" * 60)


def main() -> None:
    asyncio.run(run_queue_demo())


if __name__ == "__main__":
    main()
