"""Coalescing Application Service.

Orchestrates signal fingerprinting, temporal window candidate lookup, and incident linking.
"""

from datetime import timedelta, timezone
from typing import Sequence

from app.config import settings
from app.domain.models import SignalEvent, CoalescedIncident
from app.domain.interfaces.repositories import IncidentRepositoryInterface
from app.coalescing.fingerprint import DeterministicFingerprinter
from app.coalescing.similarity import DeterministicSimilarityProvider


class CoalescingService:
    """Service managing deduplication & aggregation of SignalEvents into CoalescedIncidents."""

    def __init__(
        self,
        repository: IncidentRepositoryInterface,
        fingerprinter: DeterministicFingerprinter | None = None,
        similarity_provider: DeterministicSimilarityProvider | None = None,
        window_seconds: int | None = None,
    ) -> None:
        self._repository = repository
        self._fingerprinter = fingerprinter or DeterministicFingerprinter()
        self._similarity_provider = similarity_provider or DeterministicSimilarityProvider()
        self._window_seconds = window_seconds or settings.COALESCING_WINDOW_SECONDS

    async def coalesce_signal(self, event: SignalEvent) -> tuple[CoalescedIncident, bool]:
        """Coalesce a normalized SignalEvent into an active incident or create a new one.

        Returns:
            Tuple of (CoalescedIncident, is_new_incident)
        """
        # Step 1: Derive deterministic fingerprint key
        coalesce_key = self._fingerprinter.generate_fingerprint(event)

        # Step 2: Compute temporal window boundary
        event_time = event.created_at if event.created_at.tzinfo else event.created_at.replace(tzinfo=timezone.utc)
        window_start = event_time - timedelta(seconds=self._window_seconds)

        # Step 3: Lookup active candidate incident within time window
        candidate = await self._repository.find_candidate_incident(
            tenant_id=event.tenant_id,
            coalesce_key=coalesce_key,
            window_start=window_start,
        )

        if candidate:
            # Step 4a: Join existing incident
            candidate.add_signal(
                event_id=event.event_id,
                source_type=event.source_type,
                event_timestamp=event_time,
            )
            await self._repository.update_incident(candidate)
            await self._repository.add_signal_link(candidate.incident_id, event.event_id)
            return candidate, False

        # Step 4b: Create new CoalescedIncident
        title = self._format_title(event)
        new_incident = CoalescedIncident(
            tenant_id=event.tenant_id,
            coalesce_key=coalesce_key,
            representative_title=title,
            source_types=[event.source_type],
            event_ids=[event.event_id],
            signal_count=1,
            coalescing_method="deterministic_fingerprint",
            first_seen=event_time,
            last_seen=event_time,
            created_at=event_time,
        )

        saved_incident = await self._repository.create_incident(new_incident)
        await self._repository.add_signal_link(saved_incident.incident_id, event.event_id)
        return saved_incident, True

    def _format_title(self, event: SignalEvent) -> str:
        """Generate human-readable representative title for incident."""
        repo = event.metadata.get("repository") if event.metadata else None
        if repo and repo != "unknown/repo":
            return f"[{event.source_type.upper()}] Incident on {repo}: {event.event_type}"
        return f"[{event.source_type.upper()}] Incident: {event.event_type}"
