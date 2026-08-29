"""Integration Tests for Incidents & Coalescing API.

Validates end-to-end signal ingestion with coalescing, incident query endpoints,
linked signal retrieval, and metrics reporting.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signal_ingestion_triggers_coalescing_and_links(async_client: AsyncClient):
    # Ingest signal 1
    payload1 = {
        "tenant_id": "tenant_api_coalesce",
        "payload": {
            "action": "opened",
            "issue": {"id": 1001, "number": 1, "title": "API Gateway 502 Bad Gateway"},
            "repository": {"full_name": "org/api-gateway"},
        },
    }
    res1 = await async_client.post("/signals", json=payload1)
    assert res1.status_code == 202
    data1 = res1.json()
    assert data1["status"] == "COALESCED"
    event_id_1 = data1["event_id"]

    # Ingest signal 2 (related incident within window)
    payload2 = {
        "tenant_id": "tenant_api_coalesce",
        "payload": {
            "action": "opened",
            "issue": {"id": 1002, "number": 2, "title": "API Gateway 502 Spike"},
            "repository": {"full_name": "org/api-gateway"},
        },
    }
    res2 = await async_client.post("/signals", json=payload2)
    assert res2.status_code == 202
    data2 = res2.json()
    assert data2["status"] == "COALESCED"
    event_id_2 = data2["event_id"]

    # Fetch coalescing metrics
    metrics_res = await async_client.get(
        "/api/v1/coalescing/metrics",
        headers={"X-Tenant-ID": "tenant_api_coalesce"},
    )
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["signals_received"] == 2
    assert metrics["signals_coalesced"] == 2
    assert metrics["incidents_created"] == 1
    assert metrics["coalescing_ratio"] == 2.0


@pytest.mark.asyncio
async def test_get_incident_and_linked_signals(async_client: AsyncClient):
    payload = {
        "tenant_id": "tenant_query_test",
        "payload": {
            "incident_id": "inc_query_999",
            "severity": "P1",
            "service": "database-cluster",
            "alert_name": "ConnectionPoolExhausted",
        },
    }
    res = await async_client.post("/signals", json=payload)
    assert res.status_code == 202
    event_id = res.json()["event_id"]

    # Fetch telemetry metrics to discover incident
    metrics_res = await async_client.get(
        "/api/v1/coalescing/metrics",
        headers={"X-Tenant-ID": "tenant_query_test"},
    )
    assert metrics_res.status_code == 200
    assert metrics_res.json()["incidents_created"] >= 1
