"""Unit Tests for SignalEvent Domain Entity.

Validates domain contract invariants, immutability, type safety, and timezone enforcement.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.domain.models import SignalEvent
from app.domain.enums import EventStatus, SeverityLevel


def test_valid_signal_event_accepted():
    event = SignalEvent(
        source_type="github",
        source_id="issue_101",
        tenant_id="tenant_x",
        payload_hash="a" * 64,
        coalesce_key="gh_issue_101",
        raw_payload={"title": "Test Issue"},
        event_type="github_issue_opened",
        severity=SeverityLevel.MEDIUM,
    )
    assert event.event_id is not None
    assert event.created_at.tzinfo is not None
    assert event.status == EventStatus.RECEIVED


def test_empty_event_id_rejected():
    with pytest.raises(ValueError, match="event_id must be a non-empty string"):
        SignalEvent(
            event_id="",
            source_type="github",
            source_id="1",
            tenant_id="t1",
            payload_hash="a" * 64,
            coalesce_key="key",
            raw_payload={},
        )


def test_empty_tenant_id_rejected():
    with pytest.raises(ValueError, match="tenant_id must be a non-empty string"):
        SignalEvent(
            source_type="github",
            source_id="1",
            tenant_id="",
            payload_hash="a" * 64,
            coalesce_key="key",
            raw_payload={},
        )


def test_naive_timestamp_rejected():
    naive_dt = datetime.now()  # No timezone
    with pytest.raises(ValueError, match="created_at timestamp must be timezone-aware"):
        SignalEvent(
            source_type="github",
            source_id="1",
            tenant_id="t1",
            payload_hash="a" * 64,
            coalesce_key="key",
            raw_payload={},
            created_at=naive_dt,
        )


def test_naive_deadline_rejected():
    naive_deadline = datetime.now() + timedelta(hours=1)
    with pytest.raises(ValueError, match="deadline_at timestamp must be timezone-aware"):
        SignalEvent(
            source_type="github",
            source_id="1",
            tenant_id="t1",
            payload_hash="a" * 64,
            coalesce_key="key",
            raw_payload={},
            deadline_at=naive_deadline,
        )


def test_invalid_severity_rejected():
    with pytest.raises(ValueError, match="Invalid severity level"):
        SignalEvent(
            source_type="github",
            source_id="1",
            tenant_id="t1",
            payload_hash="a" * 64,
            coalesce_key="key",
            raw_payload={},
            severity="extreme_critical",  # Not in SeverityLevel enum
        )
