"""Integration Test: Worker Failure & Crash Recovery.

Verifies:
- Worker claims task from queue
- Worker terminates prior to acknowledgment (unacknowledged entry remains in queue)
- RecoveryCoordinator scans pending stale entries via claim_stale_messages
- Reclaimed task is safely reprocessed and acknowledged without data loss
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, CapacityState, TenantState
from app.domain.enums import SeverityLevel, EventStatus
from app.admission.controller import AdmissionController
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService
from app.storage.repositories import EventRepository, ExecutionRepository, IdempotencyRepository
from app.worker.worker import LedgerWorker
from app.recovery.coordinator import RecoveryCoordinator


@pytest.mark.asyncio
async def test_worker_crash_and_stale_message_recovery(db_session):
    now = datetime.now(timezone.utc)
    event_repo = EventRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    idempotency_repo = IdempotencyRepository(db_session)
    broker = InMemoryWorkQueue(stream_name="ledger:recovery_stream", group_name="rec_workers")
    publisher_service = QueuePublisherService(broker=broker, event_repo=event_repo)
    val_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), mode="rule_based")
    adm_controller = AdmissionController()

    evt = SignalEvent(
        source_type="github", source_id="rec_src_1", tenant_id="tenant_rec",
        payload_hash="f" * 64, coalesce_key="k_rec", event_type="workflow_failure",
        severity=SeverityLevel.HIGH, raw_payload={"id": "rec_1"}, created_at=now,
    )
    await event_repo.save(evt)

    assessment = await val_service.assess_work_item(evt)
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="tenant_rec", quota=100.0)
    decision = adm_controller.evaluate_admission(evt, assessment, capacity, tenant, evaluation_time=now)
    await publisher_service.handle_admission_decision(evt, decision)
    await db_session.commit()

    # Worker 1 consumes message BUT "crashes" before acknowledging
    crashed_worker = LedgerWorker("crashed_worker_1", broker, event_repo, exec_repo, idempotency_repo)
    messages = await broker.consume(crashed_worker.worker_id, count=1)
    assert len(messages) == 1
    crashed_msg = messages[0]

    # Simulate crash: message remains in pending state unacknowledged
    pending = await broker.get_pending_messages()
    assert len(pending) == 1
    assert pending[0]["transport_id"] == crashed_msg.transport_id

    # Recovery Coordinator scans and reclaims stale messages (min_idle_seconds=0.0 for instant test reclaim)
    recovery_worker = LedgerWorker("recovery_worker_2", broker, event_repo, exec_repo, idempotency_repo)
    coordinator = RecoveryCoordinator(broker, recovery_worker, idempotency_repo, exec_repo)

    outcome = await coordinator.run_recovery_scan(min_idle_seconds=0.0, batch_size=10)
    await db_session.commit()

    # Verify recovery outcome metrics
    assert outcome.scanned_pending_count == 1
    assert outcome.reclaimed_count == 1
    assert outcome.retried_count == 1

    # Verify event status completed in DB
    updated_evt = await event_repo.get_by_id(evt.event_id)
    assert updated_evt.status == EventStatus.COMPLETED

    # Verify pending queue is empty after successful recovery ACK
    post_pending = await broker.get_pending_messages()
    assert len(post_pending) == 0
