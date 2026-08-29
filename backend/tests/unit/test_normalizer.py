"""Unit Tests for Event Normalizer.

Validates routing to registered adapters and fallback generic parsing.
"""

from app.ingestion.normalizer import EventNormalizer
from app.domain.enums import EventStatus


def test_normalizer_routes_to_github():
    normalizer = EventNormalizer()
    headers = {"X-GitHub-Event": "push"}
    payload = {"repository": {"id": 1}, "sender": {"id": 2}}

    event = normalizer.normalize(headers, payload, tenant_id="test_tenant")
    assert event.source_type == "github"
    assert event.status == EventStatus.RECEIVED


def test_normalizer_fallback_generic():
    normalizer = EventNormalizer()
    headers = {}
    payload = {"custom_field": "data", "ttl_seconds": 1800}

    event = normalizer.normalize(headers, payload, tenant_id="tenant_c")
    assert event.source_type == "generic_api"
    assert event.tenant_id == "tenant_c"
    assert event.coalesce_key == "api_generic"
