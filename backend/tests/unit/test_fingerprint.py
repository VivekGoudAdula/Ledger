"""Unit Tests for Deterministic Fingerprinter.

Validates key generation stability, casing/whitespace normalization, and tenant/resource isolation.
"""

from app.domain.models import SignalEvent
from app.coalescing.fingerprint import DeterministicFingerprinter


def test_fingerprint_case_insensitivity():
    fingerprinter = DeterministicFingerprinter()

    event1 = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="Tenant_Alpha",
        payload_hash="a" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "Signal-Labs/Ledger"}},
        event_type="github_issue_opened",
    )

    event2 = SignalEvent(
        source_type="GITHUB",
        source_id="2",
        tenant_id="tenant_alpha",
        payload_hash="b" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "signal-labs/ledger"}},
        event_type="GITHUB_ISSUE_OPENED",
    )

    assert fingerprinter.generate_fingerprint(event1) == fingerprinter.generate_fingerprint(event2)


def test_fingerprint_resource_isolation():
    fingerprinter = DeterministicFingerprinter()

    event1 = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="tenant_a",
        payload_hash="a" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "org/service-a"}},
        event_type="github_issue_opened",
    )

    event2 = SignalEvent(
        source_type="github",
        source_id="2",
        tenant_id="tenant_a",
        payload_hash="b" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "org/service-b"}},
        event_type="github_issue_opened",
    )

    assert fingerprinter.generate_fingerprint(event1) != fingerprinter.generate_fingerprint(event2)


def test_fingerprint_tenant_isolation():
    fingerprinter = DeterministicFingerprinter()

    event1 = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="tenant_x",
        payload_hash="a" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "org/repo"}},
    )

    event2 = SignalEvent(
        source_type="github",
        source_id="2",
        tenant_id="tenant_y",
        payload_hash="b" * 64,
        coalesce_key="key",
        raw_payload={"repository": {"full_name": "org/repo"}},
    )

    assert fingerprinter.generate_fingerprint(event1) != fingerprinter.generate_fingerprint(event2)
