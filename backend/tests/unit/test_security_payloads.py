"""Unit Tests for Security Boundaries and Payload Handling.

Validates that authorization tokens are redacted and malformed payloads are safely rejected.
"""

import pytest
from app.ingestion.sources import GitHubSourceAdapter


def test_github_adapter_strips_authorization_headers():
    adapter = GitHubSourceAdapter()
    headers = {"Authorization": "Bearer secret_github_token_12345"}
    raw_payload = {"id": "101", "type": "PushEvent", "repo": {"name": "org/repo"}}

    evt = adapter.parse_raw(headers, raw_payload, tenant_id="tenant_sec")
    # Verify sensitive token is NOT present in raw_payload or metadata
    assert "secret_github_token_12345" not in str(evt.raw_payload)
    assert "secret_github_token_12345" not in str(evt.metadata)


def test_normalizer_handles_large_nested_payloads():
    from app.ingestion.normalizer import EventNormalizer

    normalizer = EventNormalizer()
    nested_payload = {"key": "val", "nested": {"deep": [i for i in range(1000)]}}

    evt = normalizer.normalize({}, nested_payload, tenant_id="tenant_sec")
    assert evt.payload_hash is not None
    assert len(evt.payload_hash) == 64
