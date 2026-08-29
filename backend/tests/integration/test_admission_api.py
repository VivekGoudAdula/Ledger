"""Integration Tests for Admission Control API.

Validates end-to-end signal ingestion, valuation, and admission evaluation via HTTP API endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admission_api_evaluate_endpoint(async_client: AsyncClient):
    # Step 1: Ingest a signal event
    ingest_payload = {
        "tenant_id": "tenant_adm_api",
        "payload": {
            "action": "opened",
            "issue": {"id": 999, "number": 99, "title": "Critical Service Outage"},
            "repository": {"full_name": "org/prod-service"},
        },
    }
    ingest_res = await async_client.post("/signals", json=ingest_payload)
    assert ingest_res.status_code == 202
    event_id = ingest_res.json()["event_id"]

    # Step 2: Evaluate admission decision via API
    eval_payload = {
        "work_item_id": event_id,
        "work_item_type": "signal",
        "available_capacity": 100.0,
        "total_capacity": 100.0,
        "tenant_quota": 50.0,
        "tenant_current_usage": 0.0,
    }
    eval_res = await async_client.post("/api/v1/admission/evaluate", json=eval_payload)
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["work_item_id"] == event_id
    assert eval_data["decision"] in ("ADMIT", "DEFER", "SHED")
    assert eval_data["effective_value"] > 0.0
    assert "explanation" in eval_data
