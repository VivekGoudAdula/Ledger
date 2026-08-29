"""Integration Tests for Queue API Endpoints.

Validates end-to-end publishing via HTTP API endpoints and stream telemetry metrics retrieval.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_queue_api_publish_and_metrics_endpoints(async_client: AsyncClient):
    # Step 1: Ingest a signal event
    ingest_payload = {
        "tenant_id": "tenant_queue_api",
        "payload": {
            "action": "opened",
            "issue": {"id": 777, "number": 77, "title": "Critical Payment Service Timeout"},
            "repository": {"full_name": "org/payment-api"},
        },
    }
    ingest_res = await async_client.post("/signals", json=ingest_payload)
    assert ingest_res.status_code == 202
    event_id = ingest_res.json()["event_id"]

    # Step 2: Publish work item via queue API
    pub_req = {
        "work_item_id": event_id,
        "work_item_type": "signal",
    }
    pub_res = await async_client.post("/api/v1/queue/publish", json=pub_req)
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["work_item_id"] == event_id
    assert pub_data["decision"] == "ADMIT"
    assert pub_data["status"] == "QUEUED"
    assert pub_data["message"] is not None
    assert pub_data["message"]["work_item_id"] == event_id

    # Step 3: Query queue metrics via API
    metrics_res = await async_client.get("/api/v1/queue/metrics")
    assert metrics_res.status_code == 200
    metrics_data = metrics_res.json()
    assert metrics_data["stream_length"] >= 1
