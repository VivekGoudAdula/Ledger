"""Integration Tests for Signal Ingestion API.

Validates POST /signals endpoint, payload size validation, duplicate handling, and GET endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "sqlite_wal"


@pytest.mark.asyncio
async def test_post_signals_success(async_client: AsyncClient):
    payload = {
        "tenant_id": "tenant_test_post",
        "payload": {
            "action": "opened",
            "issue": {"id": 12345, "number": 10, "title": "Critical Bug"},
            "repository": {"full_name": "org/repo"},
        },
    }

    response = await async_client.post(
        "/signals",
        json=payload,
        headers={"X-GitHub-Event": "issues"},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["source_type"] == "github"
    assert data["tenant_id"] == "tenant_test_post"
    assert data["status"] in ("NORMALIZED", "COALESCED")
    assert data["is_duplicate"] is False
    assert "event_id" in data

    # Retrieve event by ID
    event_id = data["event_id"]
    get_res = await async_client.get(f"/api/v1/events/{event_id}")
    assert get_res.status_code == 200
    assert get_res.json()["event_id"] == event_id


@pytest.mark.asyncio
async def test_post_signals_duplicate_detection(async_client: AsyncClient):
    payload = {
        "tenant_id": "tenant_dedup_api",
        "payload": {
            "id": "dup_event_999",
            "action": "workflow_run",
            "status": "failed",
        },
    }

    # First request
    res1 = await async_client.post("/signals", json=payload)
    assert res1.status_code == 202
    assert res1.json()["is_duplicate"] is False

    # Second request with identical payload
    res2 = await async_client.post("/signals", json=payload)
    assert res2.status_code == 202
    assert res2.json()["is_duplicate"] is True
    assert res2.json()["event_id"] == res1.json()["event_id"]


@pytest.mark.asyncio
async def test_post_signals_malformed_json_rejected(async_client: AsyncClient):
    response = await async_client.post(
        "/signals",
        content="invalid json {",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in (400, 422)
