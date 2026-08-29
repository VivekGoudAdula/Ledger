"""Ingestion Application Service.

Orchestrates raw signal normalization, duplicate checking, event persistence, and coalescing.
"""

from typing import Any
from app.domain.models import SignalEvent
from app.domain.enums import EventStatus
from app.domain.interfaces.repositories import EventRepositoryInterface
from app.storage.repositories import DuplicateEventException
from app.ingestion.normalizer import EventNormalizer
from app.coalescing.service import CoalescingService


class IngestionService:
    """Orchestrates intake of raw signals into canonical normalized events and coalesced incidents."""

    def __init__(
        self,
        repository: EventRepositoryInterface,
        normalizer: EventNormalizer | None = None,
        coalescing_service: CoalescingService | None = None,
    ) -> None:
        self._repository = repository
        self._normalizer = normalizer or EventNormalizer()
        self._coalescing_service = coalescing_service

    async def process_signal(
        self,
        headers: dict[str, str],
        payload: dict[str, Any],
        tenant_id: str = "default",
    ) -> tuple[SignalEvent, bool]:
        """Normalize raw payload, check for duplicate, persist event, and optionally coalesce.

        Returns:
            Tuple of (SignalEvent, is_duplicate)
        """
        event = self._normalizer.normalize(headers, payload, tenant_id)
        event.mark_status(EventStatus.NORMALIZED)
        return await self.ingest_event(event)

    async def ingest_event(self, event: SignalEvent) -> tuple[SignalEvent, bool]:
        """Directly ingest a normalized SignalEvent into persistence and coalescing."""
        existing = await self._repository.get_by_payload_hash(event.tenant_id, event.payload_hash)
        if existing:
            return existing, True

        try:
            saved_event = await self._repository.save(event)
            is_duplicate = False
        except DuplicateEventException:
            existing_after_race = await self._repository.get_by_payload_hash(event.tenant_id, event.payload_hash)
            if existing_after_race:
                return existing_after_race, True
            saved_event = event
            is_duplicate = True

        if self._coalescing_service and not is_duplicate:
            await self._coalescing_service.coalesce_signal(saved_event)
            saved_event.mark_status(EventStatus.COALESCED)
            await self._repository.update_status(saved_event.event_id, EventStatus.COALESCED)

        return saved_event, is_duplicate
