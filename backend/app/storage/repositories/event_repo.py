"""Event Repository Implementation.

Implements EventRepositoryInterface using SQLAlchemy AsyncSession.
"""

from typing import Sequence
from datetime import datetime, timezone
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import SignalEvent
from app.domain.enums import EventStatus, SeverityLevel
from app.domain.interfaces.repositories import EventRepositoryInterface
from app.storage.models import EventORM


class DuplicateEventException(Exception):
    """Raised when an event with identical tenant_id and payload_hash is inserted concurrently."""
    pass


class EventRepository(EventRepositoryInterface):
    """SQLAlchemy implementation of EventRepositoryInterface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _ensure_tz(self, dt: datetime | None) -> datetime | None:
        """Ensure datetime object is timezone-aware (UTC)."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _to_domain(self, orm: EventORM) -> SignalEvent:
        """Convert ORM model to domain entity."""
        return SignalEvent(
            event_id=orm.event_id,
            source_type=orm.source_type,
            source_id=orm.source_id,
            tenant_id=orm.tenant_id,
            payload_hash=orm.payload_hash,
            coalesce_key=orm.coalesce_key,
            event_type=orm.event_type,
            severity=SeverityLevel(orm.severity),
            metadata=orm.metadata_json or {},
            raw_payload=orm.raw_payload,
            created_at=self._ensure_tz(orm.created_at),
            deadline_at=self._ensure_tz(orm.deadline_at),
            status=EventStatus(orm.status),
            retry_count=orm.retry_count,
            coalesced_into_id=orm.coalesced_into_id,
            coalesced_count=orm.coalesced_count,
        )

    async def save(self, event: SignalEvent) -> SignalEvent:
        """Persist a new SignalEvent entity."""
        orm = EventORM(
            event_id=event.event_id,
            source_type=event.source_type,
            source_id=event.source_id,
            tenant_id=event.tenant_id,
            payload_hash=event.payload_hash,
            coalesce_key=event.coalesce_key,
            event_type=event.event_type,
            severity=event.severity.value,
            metadata_json=event.metadata,
            raw_payload=event.raw_payload,
            status=event.status.value,
            retry_count=event.retry_count,
            coalesced_into_id=event.coalesced_into_id,
            coalesced_count=event.coalesced_count,
            created_at=self._ensure_tz(event.created_at),
            deadline_at=self._ensure_tz(event.deadline_at),
        )
        try:
            self._session.add(orm)
            await self._session.flush()
            return event
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateEventException(
                f"Duplicate event detected for tenant '{event.tenant_id}' with hash '{event.payload_hash}'"
            ) from exc

    async def get_by_id(self, event_id: str) -> SignalEvent | None:
        """Fetch event by primary key."""
        stmt = select(EventORM).where(EventORM.event_id == event_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_payload_hash(self, tenant_id: str, payload_hash: str) -> SignalEvent | None:
        """Fetch event by payload hash for deduplication."""
        stmt = select(EventORM).where(
            EventORM.tenant_id == tenant_id,
            EventORM.payload_hash == payload_hash,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def update_status(self, event_id: str, status: EventStatus) -> bool:
        """Update event status."""
        stmt = (
            update(EventORM)
            .where(EventORM.event_id == event_id)
            .values(status=status.value)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def update_admission_scores(
        self,
        event_id: str,
        urgency: float,
        confidence: float,
        consequence: float,
        compute_cost: float,
        admission_score: float,
        admission_decision: str,
        admission_reason: str,
    ) -> bool:
        """Persist valuation and admission metadata to EventORM for lifecycle observability.

        Called after ValueEstimationService and AdmissionController evaluate a work item,
        so the lifecycle inspector can surface real scores from the DB.
        """
        stmt = (
            update(EventORM)
            .where(EventORM.event_id == event_id)
            .values(
                urgency_score=urgency,
                confidence_score=confidence,
                consequence_score=consequence,
                estimated_compute_cost=compute_cost,
                admission_score=admission_score,
                admission_decision=admission_decision,
                admission_reason=admission_reason,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count_active_by_tenant(self, tenant_id: str) -> int:
        """Count active events for tenant."""
        active_statuses = [
            EventStatus.RECEIVED.value,
            EventStatus.NORMALIZED.value,
            EventStatus.VALUED.value,
            EventStatus.QUEUED.value,
            EventStatus.PROCESSING.value,
        ]
        stmt = select(func.count(EventORM.event_id)).where(
            EventORM.tenant_id == tenant_id,
            EventORM.status.in_(active_statuses),
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0
