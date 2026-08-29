"""Public Status & Incident Feed REST Client.

Fetches real public incident feeds from Statuspage APIs (e.g. GitHub Status) with timeout and error handling.
"""

from typing import Any
import httpx

from app.config import settings


class StatusFeedException(Exception):
    """Base exception for Status Feed API errors."""
    pass


class StatusFeedTimeoutException(StatusFeedException):
    """Raised when Status Feed request times out."""
    pass


class StatusFeedClient:
    """Async client for fetching real public status feeds."""

    def __init__(self, feed_url: str | None = None, timeout_seconds: float = 3.0) -> None:
        self._url = feed_url or getattr(settings, "STATUS_FEED_URL", "https://www.githubstatus.com/api/v2/incidents.json")
        self._timeout = timeout_seconds

    async def fetch_incidents(self) -> list[dict[str, Any]]:
        """Fetch active/historical incidents from public status feed."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "Ledger-Platform-Hackathon/0.8.0",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(self._url, headers=headers)
            except httpx.TimeoutException as exc:
                raise StatusFeedTimeoutException(f"Status feed request to {self._url} timed out: {exc}") from exc
            except httpx.RequestError as exc:
                raise StatusFeedException(f"Network error contacting Status feed: {exc}") from exc

            if response.status_code >= 400:
                raise StatusFeedException(f"Status feed returned HTTP {response.status_code}: {response.text[:200]}")

            try:
                data = response.json()
                if isinstance(data, dict) and "incidents" in data:
                    return data["incidents"]
                if isinstance(data, list):
                    return data
                raise StatusFeedException("Malformed status feed response: expected JSON object with 'incidents' array")
            except ValueError as exc:
                raise StatusFeedException(f"Invalid JSON response from Status feed: {exc}") from exc
