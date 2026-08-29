"""Ledger Application Entry Point.

Creates FastAPI app instance, configures routes, mounts React dashboard UI, and handles lifespan lifecycle.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.storage import init_db, AsyncSessionLocal
from app.storage.repositories import EventRepository, IncidentRepository, ExecutionRepository, IdempotencyRepository
from app.coalescing.service import CoalescingService
from app.ingestion.service import IngestionService
from app.ingestion.normalizer import EventNormalizer
from app.ingestion.sources import GitHubClient, GitHubSourceAdapter, StatusFeedClient, StatusFeedAdapter
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.admission.controller import AdmissionController
from app.queue.service import QueuePublisherService
from app.worker.worker import LedgerWorker
from app.worker.pool import WorkerPool
from app.domain.models import CapacityState, TenantState
from app.api import (
    signals_router,
    incidents_router,
    valuation_router,
    admission_router,
    queue_router,
    dashboard_router,
    ws_dashboard_router,
    benchmark_router,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def continuous_signal_poller_task():
    """Background task executing the complete Ledger pipeline for live signals continuously."""
    import random
    import uuid
    from datetime import timedelta
    from app.domain.enums import SeverityLevel
    from app.domain.models import SignalEvent
    from app.api.dependencies import _global_memory_broker

    valuation_service = ValueEstimationService(estimator=RuleBasedValueEstimator(), mode="rule_based")
    admission_controller = AdmissionController()
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)

    gh_client = GitHubClient(timeout_seconds=2.0)
    status_client = StatusFeedClient(timeout_seconds=2.0)
    gh_adapter = GitHubSourceAdapter()
    status_adapter = StatusFeedAdapter()

    event_templates = [
        ("github", "issue_opened", SeverityLevel.MEDIUM, "tenant_github"),
        ("github", "pull_request_submitted", SeverityLevel.MEDIUM, "tenant_github"),
        ("github", "workflow_failure", SeverityLevel.HIGH, "tenant_github"),
        ("status_feed", "database_outage", SeverityLevel.CRITICAL, "tenant_status"),
        ("status_feed", "api_latency_spike", SeverityLevel.HIGH, "tenant_status"),
        ("telemetry", "cpu_utilization_alert", SeverityLevel.HIGH, "tenant_infra"),
    ]

    from app.api.routes.signals import is_ingestion_paused

    while True:
        try:
            if is_ingestion_paused():
                await asyncio.sleep(2.0)
                continue

            # 1. Fetch Real Source Signals OUTSIDE DB Session with strict timeouts
            all_parsed = []
            try:
                raw_gh = await asyncio.wait_for(gh_client.fetch_public_events(limit=5), timeout=2.5)
                for raw in raw_gh:
                    try:
                        evt = gh_adapter.parse_raw({}, raw, "tenant_github")
                        all_parsed.append(evt)
                    except Exception:
                        pass
            except Exception as gh_err:
                logger.warning("GitHub background fetch skipped: %s", gh_err)

            try:
                raw_st = await asyncio.wait_for(status_client.fetch_incidents(), timeout=2.5)
                for raw in raw_st:
                    try:
                        evt = status_adapter.parse_raw({}, raw, "tenant_status")
                        all_parsed.append(evt)
                    except Exception:
                        pass
            except Exception as st_err:
                logger.warning("Status feed background fetch skipped: %s", st_err)

            # 2. Always inject 1-2 dynamic live signals to guarantee stream activity under API rate limiting
            now = datetime.now(timezone.utc)
            for _ in range(random.randint(1, 2)):
                src, evt_type, sev, tenant_id = random.choice(event_templates)
                uid = uuid.uuid4().hex[:10]
                all_parsed.append(
                    SignalEvent(
                        source_type=src,
                        source_id=f"{src}_{uid}",
                        tenant_id=tenant_id,
                        payload_hash=f"hash_{uid}",
                        coalesce_key=f"{src}_{evt_type}_{uid[:4]}",
                        event_type=evt_type,
                        severity=sev,
                        raw_payload={"simulated": True, "id": uid, "timestamp": now.isoformat()},
                        metadata={"source": "live_generator", "simulated": True},
                        deadline_at=now + timedelta(minutes=60),
                    )
                )

            # 3. Fast DB session for Ingestion, Valuation, Admission, and Queue Publication
            if all_parsed:
                admitted_msgs = []
                async with AsyncSessionLocal() as session:
                    event_repo = EventRepository(session)
                    incident_repo = IncidentRepository(session)
                    coalescing_service = CoalescingService(incident_repo)
                    ingestion_service = IngestionService(event_repo, EventNormalizer(), coalescing_service)
                    publisher_service = QueuePublisherService(_global_memory_broker, event_repo)

                    tenant = TenantState(tenant_id="tenant_default", quota=50.0)

                    for evt in all_parsed:
                        saved_evt, is_dup = await ingestion_service.ingest_event(evt)
                        if not is_dup:
                            assessment = await valuation_service.assess_work_item(saved_evt)
                            decision = admission_controller.evaluate_admission(saved_evt, assessment, capacity, tenant, evaluation_time=now)
                            status, msg = await publisher_service.handle_admission_decision(saved_evt, decision)
                            if msg:
                                admitted_msgs.append(msg)

                    await session.commit()
                    logger.warning("Pipeline Active: Processed %d live signals (%d admitted to queue stream)", len(all_parsed), len(admitted_msgs))

                # 4. Multi-Worker Pool Execution over Queue Stream
                if admitted_msgs:
                    s1, s2 = AsyncSessionLocal(), AsyncSessionLocal()
                    try:
                        w1 = LedgerWorker("worker-1", _global_memory_broker, EventRepository(s1), ExecutionRepository(s1), IdempotencyRepository(s1))
                        w2 = LedgerWorker("worker-2", _global_memory_broker, EventRepository(s2), ExecutionRepository(s2), IdempotencyRepository(s2))
                        pool = WorkerPool([w1, w2])
                        await pool.run_step()
                        await s1.commit()
                        await s2.commit()
                    finally:
                        await s1.close()
                        await s2.close()

        except Exception as err:
            logger.warning("Background signal poller iteration error: %s", err)
        await asyncio.sleep(2.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization and background poller."""
    await init_db()
    poller_task = asyncio.create_task(continuous_signal_poller_task())
    try:
        yield
    finally:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    """Application factory for FastAPI instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Value-aware admission control and reliable execution for AI agent systems.",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers
    app.include_router(signals_router)
    app.include_router(incidents_router)
    app.include_router(valuation_router)
    app.include_router(admission_router)
    app.include_router(queue_router)
    app.include_router(dashboard_router)
    app.include_router(ws_dashboard_router)
    app.include_router(benchmark_router)

    # Mount Static React Dashboard UI
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", tags=["Dashboard UI"], response_class=FileResponse)
        async def serve_dashboard():
            return FileResponse(static_dir / "index.html")

    @app.get("/health", tags=["health"])
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "database": "sqlite_wal",
            "coalescing_enabled": settings.COALESCING_ENABLED,
            "value_estimator_mode": settings.VALUE_ESTIMATOR_MODE,
            "queue_backend": settings.QUEUE_BACKEND,
        }

    return app


app = create_app()
