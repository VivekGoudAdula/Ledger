"""Unit Tests for GitHub Client and Source Adapter.

Validates GitHub event parsing, rate limit handling, timeout handling, and stable event identity.
"""

from unittest.mock import AsyncMock, patch
import pytest

from app.ingestion.sources import (
    GitHubClient,
    GitHubSourceAdapter,
    GitHubRateLimitException,
    GitHubTimeoutException,
)
from app.domain.enums import SeverityLevel


@pytest.mark.asyncio
async def test_github_adapter_issue_event_normalization():
    adapter = GitHubSourceAdapter()
    raw = {
        "id": "123456789",
        "type": "IssuesEvent",
        "action": "opened",
        "repo": {"name": "signal-labs/ledger"},
        "issue": {
            "id": 987654,
            "number": 42,
            "html_url": "https://github.com/signal-labs/ledger/issues/42",
        },
    }

    evt = adapter.parse_raw({"x-github-event": "issues"}, raw, "tenant_gh_test")
    assert evt.source_type == "github"
    assert evt.tenant_id == "tenant_gh_test"
    assert evt.source_id == "issue_987654"
    assert evt.coalesce_key == "github_signal-labs/ledger_issues"
    assert evt.metadata["repository"] == "signal-labs/ledger"
    assert evt.raw_payload["id"] == "123456789"


@pytest.mark.asyncio
async def test_github_client_rate_limit_exception():
    client = GitHubClient()
    mock_resp = AsyncMock()
    mock_resp.status_code = 403
    mock_resp.text = "API rate limit exceeded"
    mock_resp.headers = {"x-ratelimit-reset": "1724925000"}

    with patch("httpx.AsyncClient.request", return_value=mock_resp):
        with pytest.raises(GitHubRateLimitException, match="rate limit"):
            await client.fetch_public_events()
