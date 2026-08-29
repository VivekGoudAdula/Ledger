"""Integration Tests for Dashboard REST and WebSocket API Endpoints.

Validates GET /api/v1/dashboard/summary REST endpoint and /ws/dashboard WebSocket streaming frame.
"""

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from app.main import app


@pytest.mark.asyncio
async def test_get_dashboard_summary_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "system_status" in data
    assert "admission_breakdown" in data
    assert "workers" in data
    assert "recovery" in data
    assert "idempotency" in data
    assert "sources" in data


def test_websocket_dashboard_stream():
    client = TestClient(app)
    with client.websocket_connect("/ws/dashboard") as websocket:
        data = websocket.receive_json()
        assert "system_status" in data
        assert "ingress_rate_sec" in data
        assert "workers" in data
