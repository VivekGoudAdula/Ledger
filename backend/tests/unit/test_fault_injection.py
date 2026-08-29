"""Unit tests for Worker Fault Injection Control Plane."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.config import settings
from app.domain.enums import EventStatus, IdempotencyStatus
from app.domain.models import QueueMessage, SignalEvent, AdmissionDecision
from app.fault_injection.models import (
    WorkerState,
    FailureMode,
    WorkerFaultInjectionError,
)
from app.fault_injection.service import FaultInjectionService
from app.worker.worker import LedgerWorker
from app.recovery.coordinator import RecoveryCoordinator


@pytest.mark.asyncio
async def test_fault_injection_service_pause_and_resume():
    """Verify FaultInjectionService pause, resume, and state derivation."""
    service = FaultInjectionService()

    assert await service.is_paused("worker-1") is False

    await service.pause_worker("worker-1")
    assert await service.is_paused("worker-1") is True

    status = await service.get_worker_control_status("worker-1")
    assert status.state == WorkerState.PAUSED
    assert status.is_paused is True

    await service.resume_worker("worker-1")
    assert await service.is_paused("worker-1") is False

    status_resumed = await service.get_worker_control_status("worker-1")
    assert status_resumed.state == WorkerState.RUNNING


@pytest.mark.asyncio
async def test_fault_injection_service_inject_and_trigger_one_shot():
    """Verify fault injection trigger and one-shot auto-clearing behavior."""
    service = FaultInjectionService()
    await service.inject_failure("worker-1", FailureMode.BEFORE_EXECUTION, one_shot=True)

    mode = await service.get_active_failure_mode("worker-1")
    assert mode == FailureMode.BEFORE_EXECUTION

    # Different checkpoint should NOT trigger
    await service.check_and_trigger_fault("worker-1", FailureMode.DURING_EXECUTION)
    assert await service.get_active_failure_mode("worker-1") == FailureMode.BEFORE_EXECUTION

    # Matching checkpoint SHOULD trigger exception and clear failure
    with pytest.raises(WorkerFaultInjectionError) as exc_info:
        await service.check_and_trigger_fault("worker-1", FailureMode.BEFORE_EXECUTION)

    assert exc_info.value.failure_mode == FailureMode.BEFORE_EXECUTION
    assert await service.get_active_failure_mode("worker-1") is None

    # Status should report FAILED state
    status = await service.get_worker_control_status("worker-1")
    assert status.state == WorkerState.FAILED
    assert status.failure_count == 1


@pytest.mark.asyncio
async def test_worker_before_execution_fault_leaves_message_unacked():
    """Verify BEFORE_EXECUTION fault prevents transport message ACK."""
    service = FaultInjectionService()
    await service.inject_failure("worker-1", FailureMode.BEFORE_EXECUTION)

    broker = AsyncMock()
    event_repo = AsyncMock()
    execution_repo = AsyncMock()
    idempotency_repo = AsyncMock()

    worker = LedgerWorker(
        worker_id="worker-1",
        broker=broker,
        event_repo=event_repo,
        execution_repo=execution_repo,
        idempotency_repo=idempotency_repo,
        fault_injector=service,
    )

    msg = QueueMessage(
        work_item_id="evt_test_1",
        tenant_id="tenant_1",
        effective_value=1.0,
        value_per_compute=1.0,
        admission_decision_id="dec_1",
        transport_id="trans_100",
    )

    success = await worker.process_message(msg)

    assert success is False
    broker.acknowledge.assert_not_called()
    execution_repo.save_checkpoint.assert_not_called()


@pytest.mark.asyncio
async def test_worker_during_execution_fault_persists_checkpoint_unacked():
    """Verify DURING_EXECUTION fault saves checkpoint but leaves transport unacked."""
    service = FaultInjectionService()
    await service.inject_failure("worker-1", FailureMode.DURING_EXECUTION)

    broker = AsyncMock()
    event_repo = AsyncMock()
    execution_repo = AsyncMock()
    idempotency_repo = AsyncMock()
    idempotency_repo.claim_ownership.return_value = (True, None)

    work_item = SignalEvent(
        event_id="evt_test_2",
        tenant_id="tenant_1",
        source_type="github",
        source_id="gh_2",
        payload_hash="h2",
        coalesce_key="ck2",
        event_type="issue_opened",
        raw_payload={},
    )
    event_repo.get_by_id.return_value = work_item

    worker = LedgerWorker(
        worker_id="worker-1",
        broker=broker,
        event_repo=event_repo,
        execution_repo=execution_repo,
        idempotency_repo=idempotency_repo,
        fault_injector=service,
    )

    msg = QueueMessage(
        work_item_id="evt_test_2",
        tenant_id="tenant_1",
        effective_value=1.0,
        value_per_compute=1.0,
        admission_decision_id="dec_2",
        transport_id="trans_200",
    )

    success = await worker.process_message(msg)

    assert success is False
    execution_repo.save_checkpoint.assert_called_once()
    broker.acknowledge.assert_not_called()


@pytest.mark.asyncio
async def test_worker_after_execution_before_ack_idempotency_protection():
    """Verify AFTER_EXECUTION_BEFORE_ACK fault persists result/idempotency, but skips ACK.
    
    Then test recovery worker reclaiming the message: Idempotency hit is triggered and ACKed
    WITHOUT re-executing the action!
    """
    service = FaultInjectionService()
    await service.inject_failure("worker-1", FailureMode.AFTER_EXECUTION_BEFORE_ACK)

    broker = AsyncMock()
    event_repo = AsyncMock()
    execution_repo = AsyncMock()

    # Shared in-memory idempotency state mock
    idempotency_store = {}

    async def mock_claim_ownership(record):
        key = f"{record.tenant_id}:{record.work_item_id}:{record.action_type}"
        if key in idempotency_store:
            return False, idempotency_store[key]
        idempotency_store[key] = record
        return True, None

    async def mock_mark_completed(key, exec_id, output):
        if key in idempotency_store:
            rec = idempotency_store[key]
            rec.status = IdempotencyStatus.COMPLETED
            rec.result_payload = output

    idempotency_repo = AsyncMock()
    idempotency_repo.claim_ownership.side_effect = mock_claim_ownership
    idempotency_repo.mark_completed.side_effect = mock_mark_completed

    work_item = SignalEvent(
        event_id="evt_test_3",
        tenant_id="tenant_1",
        source_type="github",
        source_id="gh_3",
        payload_hash="h3",
        coalesce_key="ck3",
        event_type="issue_opened",
        raw_payload={},
    )
    event_repo.get_by_id.return_value = work_item

    worker1 = LedgerWorker(
        worker_id="worker-1",
        broker=broker,
        event_repo=event_repo,
        execution_repo=execution_repo,
        idempotency_repo=idempotency_repo,
        fault_injector=service,
    )

    msg = QueueMessage(
        work_item_id="evt_test_3",
        tenant_id="tenant_1",
        effective_value=1.0,
        value_per_compute=1.0,
        admission_decision_id="dec_3",
        transport_id="trans_300",
    )

    # 1. Primary worker executes: action completes, result saved, fault injected -> NO ACK
    success1 = await worker1.process_message(msg)
    assert success1 is False
    execution_repo.save_result.assert_called_once()
    broker.acknowledge.assert_not_called()

    # 2. Recovery worker reclaims message from broker PEL and calls process_message()
    recovery_worker = LedgerWorker(
        worker_id="recovery_worker",
        broker=broker,
        event_repo=event_repo,
        execution_repo=execution_repo,
        idempotency_repo=idempotency_repo,
        fault_injector=None,  # No fault on recovery worker
    )

    # Process reclaimed message
    success2 = await recovery_worker.process_message(msg, attempt=2)

    # Idempotency hit MUST safely ACK without re-executing action
    assert success2 is True
    broker.acknowledge.assert_called_once_with("trans_300")
