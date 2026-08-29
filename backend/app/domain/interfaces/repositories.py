"""Repository Interfaces.

Defines protocol interfaces for persistence, queue operations, incident coalescing storage, and valuation storage.
"""

from typing import Protocol, Sequence
from datetime import datetime

from app.domain.models import SignalEvent, ValueAssessment, CoalescedIncident
from app.domain.enums import EventStatus


class EventRepositoryInterface(Protocol):
    """Protocol for SignalEvent persistence storage."""

    async def save(self, event: SignalEvent) -> SignalEvent:
        """Persist a new signal event."""
        ...

    async def get_by_id(self, event_id: str) -> SignalEvent | None:
        """Fetch a signal event by ID."""
        ...

    async def get_by_payload_hash(self, tenant_id: str, payload_hash: str) -> SignalEvent | None:
        """Fetch event by payload hash for deduplication."""
        ...

    async def update_status(self, event_id: str, status: EventStatus) -> bool:
        """Update event status."""
        ...

    async def count_active_by_tenant(self, tenant_id: str) -> int:
        """Count in-flight / active events for a tenant."""
        ...


class IncidentRepositoryInterface(Protocol):
    """Protocol for CoalescedIncident persistence and signal linkage."""

    async def find_candidate_incident(
        self, tenant_id: str, coalesce_key: str, window_start: datetime
    ) -> CoalescedIncident | None:
        """Find active coalesced incident matching tenant and fingerprint within time window."""
        ...

    async def create_incident(self, incident: CoalescedIncident) -> CoalescedIncident:
        """Persist a new CoalescedIncident entity."""
        ...

    async def add_signal_link(self, incident_id: str, event_id: str) -> bool:
        """Link a SignalEvent to a CoalescedIncident."""
        ...

    async def update_incident(self, incident: CoalescedIncident) -> CoalescedIncident:
        """Update an existing CoalescedIncident (last_seen, signal_count, etc.)."""
        ...

    async def get_by_id(self, incident_id: str) -> CoalescedIncident | None:
        """Fetch a CoalescedIncident by ID."""
        ...

    async def get_signals_for_incident(self, incident_id: str) -> Sequence[SignalEvent]:
        """Fetch all original SignalEvents linked to an incident."""
        ...

    async def get_metrics_summary(self, tenant_id: str = "default") -> dict[str, float | int]:
        """Get summary statistics (total signals, coalesced count, incident count, ratio)."""
        ...


class ValuationRepositoryInterface(Protocol):
    """Protocol for ValueAssessment persistence and retrieval."""

    async def save_assessment(self, assessment: ValueAssessment) -> ValueAssessment:
        """Persist a ValueAssessment record."""
        ...

    async def get_latest_assessment(self, work_item_id: str) -> ValueAssessment | None:
        """Fetch latest ValueAssessment by work_item_id."""
        ...


class QueueRepositoryInterface(Protocol):
    """Protocol for queue operations and worker leases."""

    async def enqueue(self, event_id: str, priority_score: float) -> bool:
        """Enqueue an admitted event."""
        ...

    async def claim_next(self, worker_id: str, lease_seconds: int) -> SignalEvent | None:
        """Claim next highest priority queued event with an atomic lease."""
        ...

    async def release_lease(self, event_id: str, worker_id: str) -> bool:
        """Release lease back to QUEUED."""
        ...

    async def complete_job(self, event_id: str, worker_id: str) -> bool:
        """Mark job as COMPLETED."""
        ...

    async def recover_expired_leases(self) -> int:
        """Find and recover expired worker leases."""
        ...
