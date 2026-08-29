"""Unit Tests for GitHub API Client.

Validates GitHubClient error handling for rate limits, timeouts, and HTTP errors.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.ingestion.sources import (
    GitHubClient,
    GitHubRateLimitException,
    GitHubTimeoutException,
    GitHubAPIException,
)


@pytest.mark.asyncio
async def test_github_client_rate_limit_exception():
    client = GitHubClient()
    mock_response = httpx.Response(
        status_code=403,
        text="API rate limit exceeded for 127.0.0.1",
        headers={"x-ratelimit-reset": "1700000000"},
        request=httpx.Request("GET", "https://api.github.com/events"),
    )

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        with pytest.raises(GitHubRateLimitException, match="rate limit exceeded"):
            await client.fetch_public_events()


@pytest.mark.asyncio
async def test_github_client_timeout_exception():
    client = GitHubClient()

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = httpx.TimeoutException("Connection timed out")
        with pytest.raises(GitHubTimeoutException, match="timed out"):
            await client.fetch_public_events()


@pytest.mark.asyncio
async def test_github_client_http_500_exception():
    client = GitHubClient()
    mock_response = httpx.Response(
        status_code=500,
        text="Internal Server Error",
        request=httpx.Request("GET", "https://api.github.com/events"),
    )

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        with pytest.raises(GitHubAPIException, match="HTTP 500"):
            await client.fetch_public_events()


@pytest.mark.asyncio
async def test_github_client_malformed_json():
    client = GitHubClient()
    mock_response = httpx.Response(
        status_code=200,
        text='{"message": "not a list"}',  # Dict instead of list of events
        request=httpx.Request("GET", "https://api.github.com/events"),
    )

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        with pytest.raises(GitHubAPIException, match="expected list of events"):
            await client.fetch_public_events()
