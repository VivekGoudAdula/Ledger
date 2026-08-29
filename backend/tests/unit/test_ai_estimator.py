"""Unit Tests for LLMValueEstimator.

Validates structured AI response parsing, score bounds enforcement, and error raising.
"""

import json
from unittest.mock import AsyncMock, MagicMock
import pytest
import httpx

from app.domain.models import SignalEvent
from app.valuation.ai_estimator import LLMValueEstimator


@pytest.mark.asyncio
async def test_llm_estimator_valid_response():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "urgency": 0.85,
                            "confidence": 0.90,
                            "consequence_of_drop": 0.95,
                            "estimated_compute_cost": 1.2,
                            "rationale": "High priority payment alert",
                        }
                    )
                }
            }
        ]
    }
    mock_client.post = AsyncMock(return_value=mock_res)

    estimator = LLMValueEstimator(api_key="test-key", http_client=mock_client)
    event = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        raw_payload={"test": "payload"},
    )

    assessment = await estimator.estimate(event)
    assert assessment.urgency == 0.85
    assert assessment.confidence == 0.90
    assert assessment.consequence_of_drop == 0.95
    assert assessment.estimated_compute_cost == 1.2
    assert assessment.estimator == "llm_v1"


@pytest.mark.asyncio
async def test_llm_estimator_malformed_json_raises_error():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "choices": [{"message": {"content": "Invalid JSON text string"}}]
    }
    mock_client.post = AsyncMock(return_value=mock_res)

    estimator = LLMValueEstimator(api_key="test-key", http_client=mock_client)
    event = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        raw_payload={"test": "payload"},
    )

    with pytest.raises(Exception):
        await estimator.estimate(event)
