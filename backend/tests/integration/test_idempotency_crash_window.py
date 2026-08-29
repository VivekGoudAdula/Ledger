"""Integration Test: Idempotency Protection in Action-Before-ACK Crash Window.

Verifies the critical failure window:
- Worker executes logical action successfully
- DB Idempotency record marked COMPLETED
- Worker crashes before sending transport ACK (XACK)
- Retried message arrives at another worker
- DB idempotency repository detects existing COMPLETED record
- Duplicate side effect is prevented and transport ACK is issued safely
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, CapacityState, TenantState, IdempotencyRecord, generate_idempotency_key
from app.domain.enums import SeverityLevel, IdempotencyStatus
from app.admission.controller import AdmissionController
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService
from app.storage.repositories import EventRepository, ExecutionRepository, IdempotencyRepository
from app.worker.worker import LedgerWorker


@pytest.mark.asyncio
async def test_action_before_ack_crash_window_prevents_duplicate_side_effect(db_session):
    now = datetime.now(timezone.utc)
    event_repo = EventRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    idem_repo = IdempotencyRepository(db_session)
    broker = InMemoryWorkQueue(stream_name="ledger:idem_window_stream", group_name="idem_workers")
    publisher_service = QueuePublisherService(broker=broker, event_repo=event_repo)
    val_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), mode="rule_based")
    adm_controller = AdmissionController()

    evt = SignalEvent(
        source_type="github", source_id="idem_win_1", tenant_id="tenant_idem_win",
        payload_hash="9" * 64, coalesce_key="k_idem_win", event_type="pull_request_submitted",
        severity=SeverityLevel.HIGH, raw_payload={"pr": 101}, created_at=now,
    )
    await event_repo.save(evt)

    assessment = await val_service.assess_work_item(evt)
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="tenant_idem_win", quota=100.0)
    decision = adm_controller.evaluate_admission(evt, assessment, capacity, tenant, evaluation_time=now)
    _, msg = await publisher_service.handle_admission_decision(evt, decision)
    await db_session.commit()

    # Worker 1 processes the message
    worker_1 = LedgerWorker("worker_1", broker, event_repo, exec_repo, idem_repo)
    
    # 1. Action executes & completes successfully
    key = generate_idempotency_key(msg.tenant_id, msg.work_item_id, worker_1.action_type)
    claim_rec = IdempotencyRecord(
        tenant_id=msg.tenant_id,
        work_item_id=msg.work_item_id,
        action_type=worker_1.action_type,
        status=IdempotencyStatus.IN_PROGRESS,
    )
    claimed, _ = await idem_repo.claim_ownership(claim_rec)
    assert claimed is True

    # Complete side effect & mark COMPLETED in DB
    await idem_repo.mark_completed(key, "exec_123", {"action_taken": "analyzed_pr_101"})
    await db_session.commit()

    # SIMULATE CRASH BEFORE ACK: Worker 1 terminates without calling broker.acknowledge(msg.transport_id)
    # Now Worker 2 receives the exact same message on retry / reclaim
    worker_2 = LedgerWorker("worker_2", broker, event_repo, exec_repo, idem_repo)
    
    # Worker 2 processes the unacknowledged message (attempt=2)
    success = await worker_2.process_message(msg, attempt=2)
    await db_session.commit()

    # Assert worker 2 handled it via IDEMPOTENCY HIT (returns True after ACKing duplicate)
    assert success is True

    # Confirm record remains COMPLETED with original execution output (no duplicate side effect)
    record_in_db = await idem_repo.get_record(key)
    assert record_in_db is not None
    assert record_in_db.status == IdempotencyStatus.COMPLETED
    assert record_in_db.result_data["action_taken"] == "analyzed_pr_101"
