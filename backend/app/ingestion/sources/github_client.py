"""GitHub Public REST API Client.

Fetches real public events from GitHub with rate limit, timeout, and error handling.
"""

import os
from typing import Any
import httpx

from app.config import settings


class GitHubAPIException(Exception):
    """Base exception for GitHub API errors."""
    pass


class GitHubRateLimitException(GitHubAPIException):
    """Raised when GitHub API rate limit is exceeded (HTTP 403 / 429)."""
    pass


class GitHubTimeoutException(GitHubAPIException):
    """Raised when GitHub API request times out."""
    pass


class GitHubClient:
    """Async client for fetching real public events from GitHub REST API."""

    def __init__(self, token: str | None = None, timeout_seconds: float = 3.0) -> None:
        token_env = token or getattr(settings, "GITHUB_TOKEN", "") or os.getenv("GITHUB_TOKEN", "")
        if token_env and isinstance(token_env, str) and "dummy" in token_env.lower():
            token_env = None
        self._token = token_env
        self._timeout = timeout_seconds

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Ledger-Platform-Hackathon/0.1.0",
        }
        if self._token and isinstance(self._token, str) and self._token.strip():
            token_clean = self._token.strip()
            if "dummy" not in token_clean.lower():
                headers["Authorization"] = f"Bearer {token_clean}"
        return headers

    async def fetch_public_events(self, limit: int = 30) -> list[dict[str, Any]]:
        """Fetch recent public events from GitHub global events endpoint."""
        url = "https://api.github.com/events"
        return await self._request("GET", url, params={"per_page": min(limit, 100)})

    async def fetch_repo_events(self, owner: str, repo: str, limit: int = 30) -> list[dict[str, Any]]:
        """Fetch recent public events for a specific GitHub repository."""
        url = f"https://api.github.com/repos/{owner}/{repo}/events"
        return await self._request("GET", url, params={"per_page": min(limit, 100)})

    async def _request(self, method: str, url: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute HTTP request with error & rate limit handling."""
        params_dict = dict(params) if params else {}
        client_id = getattr(settings, "GITHUB_CLIENT_ID", "")
        client_secret = getattr(settings, "GITHUB_CLIENT_SECRET", "")
        if client_id and client_secret:
            params_dict["client_id"] = client_id
            params_dict["client_secret"] = client_secret

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.request(method, url, headers=self._get_headers(), params=params_dict)
            except httpx.TimeoutException as exc:
                raise GitHubTimeoutException(f"GitHub API request to {url} timed out: {exc}") from exc
            except httpx.RequestError as exc:
                raise GitHubAPIException(f"Network error contacting GitHub API: {exc}") from exc

            # If credentials are bad (e.g. Client ID passed instead of PAT), retry unauthenticated
            if response.status_code == 401:
                anon_headers = {"Accept": "application/vnd.github+json", "User-Agent": "Ledger-Platform-Hackathon/0.1.0"}
                response = await client.request(method, url, headers=anon_headers, params=params)

            # Check rate limiting
            if response.status_code in (403, 429) and "rate limit" in response.text.lower():
                reset_time = response.headers.get("x-ratelimit-reset", "unknown")
                raise GitHubRateLimitException(f"GitHub API rate limit exceeded. Resets at {reset_time}")

            if response.status_code >= 400:
                raise GitHubAPIException(
                    f"GitHub API returned HTTP {response.status_code}: {response.text[:200]}"
                )

            try:
                data = response.json()
                if not isinstance(data, list):
                    raise GitHubAPIException("Malformed GitHub response: expected list of events")
                return data
            except ValueError as exc:
                raise GitHubAPIException(f"Invalid JSON response from GitHub: {exc}") from exc
