"""Unit Tests for Signal Source Adapters.

Validates GitHub and Incident source adapters parsing logic, metadata extraction, and payload hashing.
"""

from app.ingestion.sources import GitHubSourceAdapter, IncidentSourceAdapter
from app.domain.enums import SeverityLevel


def test_github_adapter_can_handle_headers():
    adapter = GitHubSourceAdapter()
    headers = {"x-github-event": "issues"}
    payload = {"action": "opened"}
    assert adapter.can_handle(headers, payload) is True


def test_github_adapter_parse_issue():
    adapter = GitHubSourceAdapter()
    headers = {"x-github-event": "issues", "x-github-delivery": "delivery-123"}
    payload = {
        "action": "opened",
        "issue": {"id": 999, "number": 42, "title": "Memory Leak Bug"},
        "repository": {"full_name": "signal-labs/ledger"},
        "sender": {"login": "octocat"},
    }
    event = adapter.parse_raw(headers, payload, tenant_id="tenant_a")

    assert event.source_type == "github"
    assert event.source_id == "issue_999"
    assert event.coalesce_key == "github_signal-labs/ledger_issues"
    assert event.tenant_id == "tenant_a"
    assert event.severity == SeverityLevel.MEDIUM
    assert len(event.payload_hash) == 64
    assert event.deadline_at is not None
    assert event.metadata["repository"] == "signal-labs/ledger"


def test_incident_adapter_parse_alert():
    adapter = IncidentSourceAdapter()
    headers = {}
    payload = {
        "incident_id": "inc_777",
        "severity": "P0",
        "service": "billing-service",
        "alert_name": "HighLatencyAlert",
        "metric_value": 4500,
    }
    assert adapter.can_handle(headers, payload) is True

    event = adapter.parse_raw(headers, payload, tenant_id="tenant_b")

    assert event.source_type == "incident"
    assert event.source_id == "inc_777"
    assert event.coalesce_key == "incident_billing-service_HighLatencyAlert"
    assert event.tenant_id == "tenant_b"
    assert event.raw_payload["severity"] == "P0"
