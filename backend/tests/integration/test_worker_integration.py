"""Integration Tests for Worker Execution Pipeline.

Validates end-to-end signal ingestion, valuation, admission, stream publishing,
worker claim, execution checkpointing, and durable result persistence.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, CapacityState, TenantState
from app.domain.enums import SeverityLevel, EventStatus
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.admission.controller import AdmissionController
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService
from app.storage.repositories import EventRepository, ExecutionRepository
from app.worker.worker import LedgerWorker
from app.worker.pool import WorkerPool


@pytest.mark.asyncio
async def test_end_to_end_worker_execution_pipeline(db_session):
    event_repo = EventRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    broker = InMemoryWorkQueue(stream_name="ledger:integ_stream", group_name="integ_workers")
    publisher_service = QueuePublisherService(broker=broker, event_repo=event_repo)
    valuation_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), mode="rule_based")
    admission_controller = AdmissionController()

    now = datetime.now(timezone.utc)

    # Ingest critical signal event
    evt = SignalEvent(
        source_type="github",
        source_id="integ_src_1",
        tenant_id="tenant_integ",
        payload_hash="e" * 64,
        coalesce_key="k_integ",
        event_type="database_outage",
        severity=SeverityLevel.CRITICAL,
        raw_payload={"issue_id": 99, "action": "outage_alert"},
        created_at=now,
    )
    await event_repo.save(evt)

    # Valuation & Admission
    assessment = await valuation_service.assess_work_item(evt)
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="tenant_integ", quota=50.0)
    decision = admission_controller.evaluate_admission(evt, assessment, capacity, tenant, evaluation_time=now)

    # Publish to Queue Transport
    final_status, msg = await publisher_service.handle_admission_decision(evt, decision)
    assert final_status == EventStatus.QUEUED
    assert msg is not None

    # Worker Pool Execution
    workers = [LedgerWorker(f"worker-{i+1}", broker, event_repo, exec_repo) for i in range(2)]
    pool = WorkerPool(workers)

    processed_count = await pool.run_step()
    assert processed_count == 1

    # Verify event status updated to COMPLETED in database
    updated_evt = await event_repo.get_by_id(evt.event_id)
    assert updated_evt.status == EventStatus.COMPLETED

    # Verify execution checkpoint persisted
    chk = await exec_repo.get_latest_checkpoint(evt.event_id)
    assert chk is not None
    assert chk.work_item_id == evt.event_id

    # Verify execution result persisted
    result = await exec_repo.get_result_by_work_item(evt.event_id)
    assert result is not None
    assert result.status == "COMPLETED"
    assert result.output_data["work_type"] == "signal_event"
