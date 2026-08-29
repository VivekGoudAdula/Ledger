"""Integration Tests for Valuation API Endpoints.

Validates work item evaluation endpoint and stored assessment retrieval.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_valuation_api_post_assess_and_get(async_client: AsyncClient):
    # Step 1: Ingest a signal event
    ingest_payload = {
        "tenant_id": "tenant_val_api",
        "payload": {
            "action": "opened",
            "issue": {"id": 888, "number": 88, "title": "Critical DB Cluster Timeout"},
            "repository": {"full_name": "org/db-cluster"},
        },
    }
    ingest_res = await async_client.post("/signals", json=ingest_payload)
    assert ingest_res.status_code == 202
    event_id = ingest_res.json()["event_id"]

    # Step 2: Assess work item value
    assess_req = {
        "work_item_id": event_id,
        "work_item_type": "signal",
    }
    val_res = await async_client.post("/api/v1/valuation/assess", json=assess_req)
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["work_item_id"] == event_id
    assert val_data["urgency"] > 0.0
    assert val_data["expected_value"] > 0.0
    assert val_data["value_per_compute"] > 0.0

    # Step 3: Query stored assessment by work_item_id
    get_res = await async_client.get(f"/api/v1/valuation/assessments/{event_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["assessment_id"] == val_data["assessment_id"]
    assert get_data["expected_value"] == val_data["expected_value"]
