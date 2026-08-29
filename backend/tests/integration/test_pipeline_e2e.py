"""End-to-End Integration Tests for Real Signal Pipeline.

Verifies full flow using deterministic mock source data through Source Adapters, Ingestion,
Coalescing, Value Estimation, Admission Control, Queue Transport, Worker Execution, and Database Idempotency.
"""

from unittest.mock import AsyncMock
from datetime import datetime, timezone
import pytest

from app.domain.models import CapacityState, TenantState
from app.domain.enums import SeverityLevel
from app.ingestion.sources import GitHubClient, StatusFeedClient
from app.ingestion.service import IngestionService
from app.ingestion.polling import SourcePollingService
from app.coalescing.service import CoalescingService
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.admission.controller import AdmissionController
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.service import QueuePublisherService
from app.storage.repositories import EventRepository, IncidentRepository, ExecutionRepository, IdempotencyRepository
from app.worker.worker import LedgerWorker
from app.worker.pool import WorkerPool


@pytest.mark.asyncio
async def test_full_pipeline_e2e_deterministic_execution(db_session, test_session_factory):
    broker = InMemoryWorkQueue()
    now = datetime.now(timezone.utc)

    # 1. Setup Mock GitHub and Status Clients returning deterministic fixtures
    mock_gh_client = GitHubClient()
    mock_gh_client.fetch_public_events = AsyncMock(return_value=[{
        "id": "e2e_gh_100",
        "type": "IssuesEvent",
        "action": "opened",
        "repo": {"name": "signal-labs/ledger"},
        "issue": {"id": 1001, "number": 1, "html_url": "https://github.com/signal-labs/ledger/issues/1"},
    }])

    mock_status_client = StatusFeedClient()
    mock_status_client.fetch_incidents = AsyncMock(return_value=[{
        "id": "e2e_st_200",
        "name": "API Gateway Timeout",
        "impact": "critical",
        "status": "investigating",
    }])

    # 2. Services Initialization
    event_repo = EventRepository(db_session)
    incident_repo = IncidentRepository(db_session)
    coalescing_service = CoalescingService(incident_repo)
    ingestion_service = IngestionService(event_repo, coalescing_service)
    polling_service = SourcePollingService(
        ingestion_service=ingestion_service,
        broker=broker,
        github_client=mock_gh_client,
        status_client=mock_status_client,
    )

    valuation_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), mode="rule_based")
    admission_controller = AdmissionController()
    publisher_service = QueuePublisherService(broker, event_repo)
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="tenant_e2e", quota=50.0)

    # 3. Execute Source Polling Cycle
    poll_res = await polling_service.run_full_polling_cycle(
        gh_tenant="tenant_e2e",
        status_tenant="tenant_e2e",
        telemetry_tenant="tenant_e2e",
    )
    assert poll_res["total_ingested"] >= 2

    # 4. Fetch Ingested Events and Evaluate Valuation & Admission Control
    events_in_db = [
        await event_repo.get_by_id(evt.event_id)
        for evt in await polling_service.poll_github(tenant_id="tenant_e2e", limit=2)
    ]
    events_in_db = [e for e in events_in_db if e is not None]

    admitted_events = []
    for evt in events_in_db:
        assessment = await valuation_service.assess_work_item(evt)
        decision = admission_controller.evaluate_admission(evt, assessment, capacity, tenant, evaluation_time=now)
        status, msg = await publisher_service.handle_admission_decision(evt, decision)
        if msg:
            admitted_events.append(evt)

    await db_session.commit()
    assert len(admitted_events) >= 1

    # 5. Execute Multi-Worker Pool Processing
    s1, s2 = test_session_factory(), test_session_factory()
    try:
        w1 = LedgerWorker("worker-1", broker, EventRepository(s1), ExecutionRepository(s1), IdempotencyRepository(s1))
        w2 = LedgerWorker("worker-2", broker, EventRepository(s2), ExecutionRepository(s2), IdempotencyRepository(s2))
        pool = WorkerPool([w1, w2])

        processed = await pool.run_step()
        assert processed >= 1

        # 6. Verify Durable Persistence & Idempotency Records
        exec_repo = ExecutionRepository(s1)
        res1 = await exec_repo.get_result_by_work_item(admitted_events[0].event_id)
        assert res1 is not None
        assert res1.status == "COMPLETED"
    finally:
        await s1.close()
        await s2.close()
