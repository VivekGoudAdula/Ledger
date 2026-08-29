"""Unit Tests for Public Status Feed Client and Adapter.

Validates status feed incident parsing, impact/severity mapping, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.ingestion.sources import StatusFeedClient, StatusFeedAdapter, StatusFeedException
from app.domain.enums import SeverityLevel


@pytest.mark.asyncio
async def test_status_adapter_incident_normalization():
    adapter = StatusFeedAdapter()
    raw = {
        "id": "inc_abc123",
        "name": "Database Connection Degradation",
        "impact": "critical",
        "status": "investigating",
        "shortlink": "https://st.us/123",
    }

    evt = adapter.parse_raw({}, raw, "tenant_status_test")
    assert evt.source_type == "status_feed"
    assert evt.source_id == "status_inc_abc123"
    assert evt.severity == SeverityLevel.CRITICAL
    assert evt.coalesce_key == "status_critical_inc_abc1"


@pytest.mark.asyncio
async def test_status_client_malformed_json_exception():
    client = StatusFeedClient()
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(side_effect=ValueError("Invalid JSON"))

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        with pytest.raises(StatusFeedException, match="Invalid JSON"):
            await client.fetch_incidents()
