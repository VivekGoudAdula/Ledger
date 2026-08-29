"""Unit Tests for Coalescing Service.

Validates candidate lookup within temporal windows, incident joining, and event linking.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.domain.models import SignalEvent
from app.storage.repositories import IncidentRepository, EventRepository
from app.coalescing.service import CoalescingService


@pytest.mark.asyncio
async def test_signals_within_window_coalesce(db_session):
    event_repo = EventRepository(db_session)
    incident_repo = IncidentRepository(db_session)
    service = CoalescingService(repository=incident_repo, window_seconds=300)

    now = datetime.now(timezone.utc)

    event1 = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="tenant_window",
        payload_hash="a" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "org/repo"}},
        created_at=now,
    )
    await event_repo.save(event1)

    event2 = SignalEvent(
        source_type="github",
        source_id="2",
        tenant_id="tenant_window",
        payload_hash="b" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "org/repo"}},
        created_at=now + timedelta(seconds=30),  # 30 seconds later (inside window)
    )
    await event_repo.save(event2)

    inc1, is_new1 = await service.coalesce_signal(event1)
    assert is_new1 is True
    assert inc1.signal_count == 1

    inc2, is_new2 = await service.coalesce_signal(event2)
    assert is_new2 is False
    assert inc2.incident_id == inc1.incident_id
    assert inc2.signal_count == 2
    assert event1.event_id in inc2.event_ids
    assert event2.event_id in inc2.event_ids


@pytest.mark.asyncio
async def test_signals_outside_window_create_new_incident(db_session):
    event_repo = EventRepository(db_session)
    incident_repo = IncidentRepository(db_session)
    service = CoalescingService(repository=incident_repo, window_seconds=300)

    now = datetime.now(timezone.utc)

    event1 = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="tenant_outside",
        payload_hash="a" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "org/repo"}},
        created_at=now - timedelta(seconds=600),  # 10 minutes ago
    )
    await event_repo.save(event1)

    event2 = SignalEvent(
        source_type="github",
        source_id="2",
        tenant_id="tenant_outside",
        payload_hash="b" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "org/repo"}},
        created_at=now,  # Now (10 minutes later > 300s window)
    )
    await event_repo.save(event2)

    inc1, is_new1 = await service.coalesce_signal(event1)
    assert is_new1 is True

    inc2, is_new2 = await service.coalesce_signal(event2)
    assert is_new2 is True  # New incident created!
    assert inc2.incident_id != inc1.incident_id
