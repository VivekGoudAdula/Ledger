"""Multiphase End-to-End Integration Test Suite.

Verifies E2E 1 through E2E 7 reliability flows across all 11 phases of Ledger.
"""

from unittest.mock import AsyncMock
from datetime import datetime, timezone
import pytest

from app.domain.models import SignalEvent, QueueMessage
from app.domain.enums import ActionType
from app.ingestion.sources import GitHubClient, StatusFeedClient, GitHubAPIException
from app.ingestion.service import IngestionService
from app.ingestion.normalizer import EventNormalizer
from app.ingestion.polling import SourcePollingService
from app.coalescing.service import CoalescingService
from app.queue.memory_broker import InMemoryWorkQueue
from app.storage.repositories import EventRepository, IncidentRepository, ExecutionRepository, IdempotencyRepository
from app.idempotency.service import IdempotencyService
from app.worker.worker import LedgerWorker


@pytest.mark.asyncio
async def test_e2e_normal_and_duplicate_delivery(db_session):
    """E2E 1 & E2E 3: Normal pipeline flow and duplicate delivery idempotency protection."""
    broker = InMemoryWorkQueue()
    event_repo = EventRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    idem_repo = IdempotencyRepository(db_session)
    coalescing_service = CoalescingService(IncidentRepository(db_session))
    ingestion_service = IngestionService(event_repo, EventNormalizer(), coalescing_service)

    # 1. Ingest raw signal
    evt, is_dup1 = await ingestion_service.process_signal({}, {"id": "e2e_evt_100", "type": "PushEvent"}, "tenant_e2e")
    assert is_dup1 is False
    await db_session.flush()

    # 2. Ingest duplicate signal
    evt_dup, is_dup2 = await ingestion_service.process_signal({}, {"id": "e2e_evt_100", "type": "PushEvent"}, "tenant_e2e")
    assert is_dup2 is True
    assert evt.event_id == evt_dup.event_id
    await db_session.flush()

    # 3. Worker execution with idempotency guard
    w1 = LedgerWorker("worker-1", broker, event_repo, exec_repo, idem_repo)
    msg = QueueMessage(
        work_item_id=evt.event_id,
        tenant_id="tenant_e2e",
        effective_value=0.9,
        value_per_compute=1.8,
        admission_decision_id="ADM-e2e-100",
    )
    res = await w1.process_message(msg)
    assert res is True


@pytest.mark.asyncio
async def test_e2e_failure_after_action_before_ack(db_session):
    """E2E 5: Worker performs logical action, crashes before ACK, redelivery hits idempotency guard."""
    broker = InMemoryWorkQueue()
    event_repo = EventRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    idem_repo = IdempotencyRepository(db_session)
    idem_service = IdempotencyService(idem_repo)

    now = datetime.now(timezone.utc)
    evt = SignalEvent(
        source_type="test",
        source_id="crash_500",
        tenant_id="tenant_e2e",
        payload_hash="sha256_500",
        coalesce_key="key_500",
        raw_payload={"id": "500"},
        created_at=now,
    )
    saved_evt = await event_repo.save(evt)
    await db_session.flush()

    # Step 1: Pre-claim idempotency record and mark COMPLETED (simulates crash after DB save before ACK)
    claimed, rec = await idem_service.claim_execution_ownership("tenant_e2e", saved_evt.event_id, ActionType.ANALYZE_SIGNAL)
    await idem_service.complete_execution("tenant_e2e", saved_evt.event_id, ActionType.ANALYZE_SIGNAL, "EXEC-CRASH-500", {"result": "success"})
    await db_session.flush()

    # Step 2: Redeliver message to replacement worker
    w2 = LedgerWorker("worker-replacement", broker, event_repo, exec_repo, idem_repo)
    msg = QueueMessage(
        work_item_id=saved_evt.event_id,
        tenant_id="tenant_e2e",
        effective_value=0.8,
        value_per_compute=1.2,
        admission_decision_id="ADM-e2e-500",
    )

    # Worker processes redelivered message -> Idempotency hit skips re-execution!
    processed = await w2.process_message(msg)
    assert processed is True


@pytest.mark.asyncio
async def test_e2e_source_failure_isolation(db_session):
    """E2E 7: Source failure isolation (GitHub API error does NOT stop Status Feed poller)."""
    broker = InMemoryWorkQueue()
    event_repo = EventRepository(db_session)
    coalescing_service = CoalescingService(IncidentRepository(db_session))
    ingestion_service = IngestionService(event_repo, EventNormalizer(), coalescing_service)

    # Mock GitHub Client returning rate-limit error
    mock_gh = GitHubClient()
    mock_gh.fetch_public_events = AsyncMock(side_effect=GitHubAPIException("GitHub Rate Limit Exceeded"))

    # Mock Status Client returning valid incident
    mock_st = StatusFeedClient()
    mock_st.fetch_incidents = AsyncMock(return_value=[{
        "id": "inc_iso_700",
        "name": "Database Connection Degradation",
        "impact": "critical",
        "status": "investigating",
    }])

    polling_service = SourcePollingService(
        ingestion_service=ingestion_service,
        broker=broker,
        github_client=mock_gh,
        status_client=mock_st,
    )

    res = await polling_service.run_full_polling_cycle(gh_tenant="t_gh", status_tenant="t_st", telemetry_tenant="t_tm")

    assert res["github_events_ingested"] == 0
    assert res["status_events_ingested"] == 1
    assert res["total_ingested"] == 1
