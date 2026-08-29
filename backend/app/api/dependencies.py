"""FastAPI Dependency Injection Providers.

Provides injected database sessions, repositories, and application services to endpoints.
"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.storage.database import get_db_session
from app.storage.repositories import EventRepository, IncidentRepository, ValuationRepository, ExecutionRepository, IdempotencyRepository
from app.coalescing.service import CoalescingService
from app.ingestion.service import IngestionService
from app.ingestion.polling import SourcePollingService
from app.valuation.service import ValueEstimationService
from app.admission.controller import AdmissionController
from app.domain.interfaces.queue import WorkQueueInterface
from app.queue.memory_broker import InMemoryWorkQueue
from app.queue.redis_broker import RedisStreamBroker
from app.queue.service import QueuePublisherService
from app.idempotency.service import IdempotencyService
from app.worker.worker import LedgerWorker
from app.recovery.coordinator import RecoveryCoordinator
from app.dashboard.service import DashboardService


async def get_event_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EventRepository:
    """Provide EventRepository dependency bound to current DB session."""
    return EventRepository(session)


async def get_incident_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IncidentRepository:
    """Provide IncidentRepository dependency bound to current DB session."""
    return IncidentRepository(session)


async def get_valuation_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ValuationRepository:
    """Provide ValuationRepository dependency bound to current DB session."""
    return ValuationRepository(session)


async def get_execution_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExecutionRepository:
    """Provide ExecutionRepository dependency bound to current DB session."""
    return ExecutionRepository(session)


async def get_idempotency_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IdempotencyRepository:
    """Provide IdempotencyRepository dependency bound to current DB session."""
    return IdempotencyRepository(session)


async def get_idempotency_service(
    idempotency_repo: Annotated[IdempotencyRepository, Depends(get_idempotency_repository)],
) -> IdempotencyService:
    """Provide IdempotencyService dependency."""
    return IdempotencyService(repository=idempotency_repo)


async def get_coalescing_service(
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
) -> CoalescingService:
    """Provide CoalescingService dependency."""
    return CoalescingService(repository=incident_repo)


async def get_ingestion_service(
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
    coalescing_service: Annotated[CoalescingService, Depends(get_coalescing_service)],
) -> IngestionService:
    """Provide IngestionService dependency integrated with coalescing."""
    return IngestionService(repository=event_repo, coalescing_service=coalescing_service)


async def get_valuation_service(
    valuation_repo: Annotated[ValuationRepository, Depends(get_valuation_repository)],
) -> ValueEstimationService:
    """Provide ValueEstimationService dependency with persistence."""
    return ValueEstimationService(repository=valuation_repo)


async def get_admission_controller() -> AdmissionController:
    """Provide AdmissionController dependency."""
    return AdmissionController()


from app.fault_injection.service import FaultInjectionService
from app.worker.pool import WorkerPool

_global_memory_broker = InMemoryWorkQueue()
_global_fault_injector = FaultInjectionService()
_global_worker_pool: WorkerPool | None = None


def set_global_worker_pool(pool: WorkerPool) -> None:
    """Set global WorkerPool singleton for API dependency access."""
    global _global_worker_pool
    _global_worker_pool = pool


def get_global_worker_pool() -> WorkerPool | None:
    """Retrieve global WorkerPool singleton."""
    return _global_worker_pool


async def get_fault_injector() -> FaultInjectionService:
    """Provide FaultInjectionService dependency."""
    return _global_fault_injector


async def get_queue_broker() -> WorkQueueInterface:
    """Provide WorkQueueInterface dependency based on configured QUEUE_BACKEND."""
    if settings.QUEUE_BACKEND == "redis":
        return RedisStreamBroker()
    return _global_memory_broker


async def get_queue_publisher_service(
    broker: Annotated[WorkQueueInterface, Depends(get_queue_broker)],
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> QueuePublisherService:
    """Provide QueuePublisherService dependency."""
    return QueuePublisherService(broker=broker, event_repo=event_repo)


async def get_recovery_coordinator(
    broker: Annotated[WorkQueueInterface, Depends(get_queue_broker)],
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
    execution_repo: Annotated[ExecutionRepository, Depends(get_execution_repository)],
    idempotency_repo: Annotated[IdempotencyRepository, Depends(get_idempotency_repository)],
) -> RecoveryCoordinator:
    """Provide RecoveryCoordinator dependency."""
    worker = LedgerWorker(
        worker_id="recovery_worker",
        broker=broker,
        event_repo=event_repo,
        execution_repo=execution_repo,
        idempotency_repo=idempotency_repo,
        fault_injector=_global_fault_injector,
    )
    return RecoveryCoordinator(
        broker=broker,
        worker=worker,
        idempotency_repo=idempotency_repo,
        execution_repo=execution_repo,
    )


async def get_source_polling_service(
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
    broker: Annotated[WorkQueueInterface, Depends(get_queue_broker)],
) -> SourcePollingService:
    """Provide SourcePollingService dependency."""
    return SourcePollingService(ingestion_service=ingestion_service, broker=broker)


async def get_dashboard_service(
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
    execution_repo: Annotated[ExecutionRepository, Depends(get_execution_repository)],
    idempotency_repo: Annotated[IdempotencyRepository, Depends(get_idempotency_repository)],
    broker: Annotated[WorkQueueInterface, Depends(get_queue_broker)],
) -> DashboardService:
    """Provide DashboardService dependency."""
    return DashboardService(
        event_repo=event_repo,
        execution_repo=execution_repo,
        idempotency_repo=idempotency_repo,
        broker=broker,
        pool=_global_worker_pool,
    )
