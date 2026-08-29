"""Unit Tests for Queue Broker Stale Message Reclaim.

Validates claim_stale_messages idle threshold filtering in InMemoryWorkQueue.
"""

import asyncio
import pytest

from app.domain.models import SignalEvent, AdmissionDecision
from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum, AdmissionReason
from app.queue.memory_broker import InMemoryWorkQueue


@pytest.mark.asyncio
async def test_stale_claim_idle_threshold_filtering():
    broker = InMemoryWorkQueue()
    evt = SignalEvent(
        source_type="github",
        source_id="src_stale",
        tenant_id="tenant_stale",
        payload_hash="a" * 64,
        coalesce_key="key_stale",
        raw_payload={"detail": "stale test"},
    )
    dec = AdmissionDecision(
        decision=AdmissionDecisionEnum.ADMIT,
        work_item_id=evt.event_id,
        reason=AdmissionReason.ADMITTED_CAPACITY_AVAILABLE,
        effective_value=0.8,
        value_per_compute=1.0,
        capacity_required=1.0,
        capacity_available=50.0,
        tenant_id="tenant_stale",
        explanation="test",
    )
    msg = await broker.publish(evt, dec)

    # Consume message so it enters pending state
    consumed = await broker.consume("worker-1", count=1)
    assert len(consumed) == 1

    # Attempt immediate claim with 10,000ms idle threshold (Should NOT be reclaimed!)
    claimed_immediate = await broker.claim_stale_messages("recovery-worker", min_idle_ms=10000)
    assert len(claimed_immediate) == 0

    # Claim with 0ms idle threshold (Should BE reclaimed!)
    claimed_stale = await broker.claim_stale_messages("recovery-worker", min_idle_ms=0)
    assert len(claimed_stale) == 1
    assert claimed_stale[0].work_item_id == evt.event_id
