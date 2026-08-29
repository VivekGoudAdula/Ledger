"""Unit Tests for DeterministicExecutionHandler.

Validates deterministic analysis outputs over SignalEvent and CoalescedIncident entities.
"""

import pytest

from app.domain.models import SignalEvent, CoalescedIncident
from app.worker.handler import DeterministicExecutionHandler


@pytest.mark.asyncio
async def test_execution_handler_signal_event():
    handler = DeterministicExecutionHandler()
    event = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        raw_payload={"action": "test_payload"},
    )

    output = await handler.execute(event)
    assert output["work_type"] == "signal_event"
    assert output["event_id"] == event.event_id
    assert output["tenant_id"] == "t1"
    assert "payload_sha256" in output


@pytest.mark.asyncio
async def test_execution_handler_coalesced_incident():
    handler = DeterministicExecutionHandler()
    incident = CoalescedIncident(
        tenant_id="t1",
        coalesce_key="k1",
        representative_title="DB Spike",
        signal_count=5,
        coalescing_method="fingerprint",
    )

    output = await handler.execute(incident)
    assert output["work_type"] == "coalesced_incident"
    assert output["incident_id"] == incident.incident_id
    assert output["signal_count"] == 5
