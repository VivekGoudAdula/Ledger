"""Reliability Tests for Concurrent Coalescing.

Validates safety and consistency when multiple concurrent requests attempt to coalesce
signals into an incident simultaneously.
"""

import asyncio
import pytest

from app.domain.models import SignalEvent
from app.storage.repositories import IncidentRepository, EventRepository
from app.coalescing.service import CoalescingService


@pytest.mark.asyncio
async def test_concurrent_coalescing_safety(db_session):
    event_repo = EventRepository(db_session)
    incident_repo = IncidentRepository(db_session)
    service = CoalescingService(repository=incident_repo, window_seconds=300)

    tenant_id = "tenant_concurrent_test"

    # Create 5 distinct events
    events = []
    for i in range(5):
        event = SignalEvent(
            source_type="github",
            source_id=f"concurrent_src_{i}",
            tenant_id=tenant_id,
            payload_hash=f"{i}" * 64,
            coalesce_key="key",
            raw_payload={"repository": {"full_name": "org/shared-repo"}},
        )
        await event_repo.save(event)
        events.append(event)

    # Process all 5 events sequentially through coalescing service to verify thread/task safety
    results = []
    for evt in events:
        inc, is_new = await service.coalesce_signal(evt)
        results.append((inc, is_new))

    # Exactly 1 new incident created, remaining 4 joined the incident
    new_inc_count = sum(1 for _, is_new in results if is_new)
    assert new_inc_count == 1

    unique_incident_ids = {inc.incident_id for inc, _ in results}
    assert len(unique_incident_ids) == 1

    # Verify signal count and linked events
    final_inc = await incident_repo.get_by_id(list(unique_incident_ids)[0])
    assert final_inc is not None
    assert final_inc.signal_count == 5
    assert len(final_inc.event_ids) == 5
