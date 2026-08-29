"""Incident Repository Implementation.

Implements IncidentRepositoryInterface using SQLAlchemy AsyncSession.
"""

from typing import Sequence
from datetime import datetime, timezone
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import SignalEvent, CoalescedIncident
from app.domain.enums import EventStatus, SeverityLevel
from app.domain.interfaces.repositories import IncidentRepositoryInterface
from app.storage.models import EventORM, IncidentORM, IncidentSignalLinkORM


class IncidentRepository(IncidentRepositoryInterface):
    """SQLAlchemy implementation of IncidentRepositoryInterface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _ensure_tz(self, dt: datetime | None) -> datetime | None:
        """Ensure datetime object is timezone-aware (UTC)."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _to_domain_incident(self, orm: IncidentORM, event_ids: list[str] | None = None) -> CoalescedIncident:
        """Convert IncidentORM to domain entity."""
        return CoalescedIncident(
            incident_id=orm.incident_id,
            tenant_id=orm.tenant_id,
            coalesce_key=orm.coalesce_key,
            representative_title=orm.representative_title,
            source_types=orm.source_types or [],
            event_ids=event_ids or [],
            signal_count=orm.signal_count,
            coalescing_method=orm.coalescing_method,
            first_seen=self._ensure_tz(orm.first_seen),
            last_seen=self._ensure_tz(orm.last_seen),
            created_at=self._ensure_tz(orm.created_at),
        )

    async def find_candidate_incident(
        self, tenant_id: str, coalesce_key: str, window_start: datetime
    ) -> CoalescedIncident | None:
        """Find active candidate incident matching tenant & key within temporal window.

        Uses indexed lookup on (tenant_id, coalesce_key, last_seen) to avoid table scans.
        """
        stmt = (
            select(IncidentORM)
            .where(
                IncidentORM.tenant_id == tenant_id,
                IncidentORM.coalesce_key == coalesce_key,
                IncidentORM.last_seen >= window_start,
            )
            .order_by(IncidentORM.last_seen.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None

        # Fetch linked event_ids for candidate
        link_stmt = select(IncidentSignalLinkORM.event_id).where(
            IncidentSignalLinkORM.incident_id == orm.incident_id
        )
        link_res = await self._session.execute(link_stmt)
        event_ids = list(link_res.scalars().all())

        return self._to_domain_incident(orm, event_ids)

    async def create_incident(self, incident: CoalescedIncident) -> CoalescedIncident:
        """Persist a new CoalescedIncident entity."""
        orm = IncidentORM(
            incident_id=incident.incident_id,
            tenant_id=incident.tenant_id,
            coalesce_key=incident.coalesce_key,
            representative_title=incident.representative_title,
            source_types=incident.source_types,
            signal_count=incident.signal_count,
            coalescing_method=incident.coalescing_method,
            first_seen=self._ensure_tz(incident.first_seen),
            last_seen=self._ensure_tz(incident.last_seen),
            created_at=self._ensure_tz(incident.created_at),
        )
        self._session.add(orm)
        await self._session.flush()
        return incident

    async def add_signal_link(self, incident_id: str, event_id: str) -> bool:
        """Link a SignalEvent to a CoalescedIncident."""
        link = IncidentSignalLinkORM(incident_id=incident_id, event_id=event_id)
        try:
            self._session.add(link)
            await self._session.flush()
            return True
        except IntegrityError:
            await self._session.rollback()
            return False  # Already linked

    async def update_incident(self, incident: CoalescedIncident) -> CoalescedIncident:
        """Update last_seen, signal_count, and source_types for an incident."""
        stmt = (
            update(IncidentORM)
            .where(IncidentORM.incident_id == incident.incident_id)
            .values(
                last_seen=self._ensure_tz(incident.last_seen),
                signal_count=incident.signal_count,
                source_types=incident.source_types,
            )
        )
        await self._session.execute(stmt)
        return incident

    async def get_by_id(self, incident_id: str) -> CoalescedIncident | None:
        """Fetch a CoalescedIncident by ID."""
        stmt = select(IncidentORM).where(IncidentORM.incident_id == incident_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None

        link_stmt = select(IncidentSignalLinkORM.event_id).where(
            IncidentSignalLinkORM.incident_id == incident_id
        )
        link_res = await self._session.execute(link_stmt)
        event_ids = list(link_res.scalars().all())

        return self._to_domain_incident(orm, event_ids)

    async def get_signals_for_incident(self, incident_id: str) -> Sequence[SignalEvent]:
        """Fetch all original SignalEvents linked to an incident."""
        stmt = (
            select(EventORM)
            .join(IncidentSignalLinkORM, EventORM.event_id == IncidentSignalLinkORM.event_id)
            .where(IncidentSignalLinkORM.incident_id == incident_id)
            .order_by(EventORM.created_at.asc())
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [
            SignalEvent(
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
            )
            for orm in orms
        ]

    async def get_metrics_summary(self, tenant_id: str = "default") -> dict[str, float | int]:
        """Calculate coalescing performance metrics for tenant."""
        # Total signals received
        sig_stmt = select(func.count(EventORM.event_id)).where(EventORM.tenant_id == tenant_id)
        sig_res = await self._session.execute(sig_stmt)
        total_signals = sig_res.scalar() or 0

        # Total incidents created
        inc_stmt = select(func.count(IncidentORM.incident_id)).where(IncidentORM.tenant_id == tenant_id)
        inc_res = await self._session.execute(inc_stmt)
        total_incidents = inc_res.scalar() or 0

        # Linked signals
        link_stmt = (
            select(func.count(IncidentSignalLinkORM.link_id))
            .join(IncidentORM, IncidentSignalLinkORM.incident_id == IncidentORM.incident_id)
            .where(IncidentORM.tenant_id == tenant_id)
        )
        link_res = await self._session.execute(link_stmt)
        coalesced_signals = link_res.scalar() or 0

        ratio = round(total_signals / max(total_incidents, 1), 2)
        avg_signals = round(coalesced_signals / max(total_incidents, 1), 2)

        return {
            "signals_received": total_signals,
            "signals_coalesced": coalesced_signals,
            "incidents_created": total_incidents,
            "coalescing_ratio": ratio,
            "avg_signals_per_incident": avg_signals,
        }
