"""AI/LLM-Backed Value Estimator.

Provides AI semantic estimation for work items with strict output score validation.
"""

import json
from typing import Any
import httpx

from app.config import settings
from app.domain.models import SignalEvent, CoalescedIncident, ValueAssessment
from app.domain.interfaces.estimator import ValueEstimatorInterface


class LLMValueEstimator(ValueEstimatorInterface):
    """Estimates work item value dimensions using structured AI model responses."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key or settings.AI_ESTIMATOR_API_KEY
        self._timeout = timeout_seconds or settings.AI_ESTIMATOR_TIMEOUT_SECONDS
        self._http_client = http_client

    async def estimate(
        self, work_item: SignalEvent | CoalescedIncident
    ) -> ValueAssessment:
        """Estimate urgency, confidence, consequence, compute cost, and rationale via LLM."""
        prompt_payload = self._build_prompt(work_item)
        response_data = await self._query_llm(prompt_payload)
        return self._parse_and_validate_response(work_item, response_data)

    def _build_prompt(self, work_item: SignalEvent | CoalescedIncident) -> dict[str, Any]:
        """Format work item into structured prompt payload."""
        if isinstance(work_item, SignalEvent):
            return {
                "work_item_id": work_item.event_id,
                "work_item_type": "signal",
                "source_type": work_item.source_type,
                "event_type": work_item.event_type,
                "severity": work_item.severity.value,
                "metadata": work_item.metadata,
                "raw_payload": work_item.raw_payload,
            }
        return {
            "work_item_id": work_item.incident_id,
            "work_item_type": "incident",
            "coalesce_key": work_item.coalesce_key,
            "title": work_item.representative_title,
            "source_types": work_item.source_types,
            "signal_count": work_item.signal_count,
        }

    async def _query_llm(self, prompt_payload: dict[str, Any]) -> dict[str, Any]:
        """Query LLM endpoint or simulate structured response if no client configured."""
        if not self._http_client:
            # If no HTTP client is injected or configured, raise exception to trigger fallback
            raise RuntimeError("LLM Estimator client unconfigured or unavailable")

        # Send request to configured LLM endpoint
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an AI work item value estimator for an admission control system. "
                        "Return ONLY a JSON object with keys: urgency (float 0-1), confidence (float 0-1), "
                        "consequence_of_drop (float 0-1), estimated_compute_cost (float > 0), rationale (string)."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt_payload)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        res = await self._http_client.post(url, json=body, headers=headers, timeout=self._timeout)
        if res.status_code != 200:
            raise RuntimeError(f"LLM API returned HTTP error: {res.status_code}")

        data = res.json()
        raw_text = data["choices"][0]["message"]["content"]
        return json.loads(raw_text)

    def _parse_and_validate_response(
        self, work_item: SignalEvent | CoalescedIncident, data: dict[str, Any]
    ) -> ValueAssessment:
        """Parse raw response dict and validate against domain score constraints."""
        required_keys = {"urgency", "confidence", "consequence_of_drop", "estimated_compute_cost", "rationale"}
        if not required_keys.issubset(data.keys()):
            raise ValueError(f"LLM response missing required keys: {required_keys - data.keys()}")

        work_id = work_item.event_id if isinstance(work_item, SignalEvent) else work_item.incident_id
        work_type = "signal" if isinstance(work_item, SignalEvent) else "incident"
        deadline = work_item.deadline_at if isinstance(work_item, SignalEvent) else None

        # ValueAssessment __post_init__ will strictly validate score bounds
        return ValueAssessment(
            work_item_id=work_id,
            work_item_type=work_type,
            urgency=float(data["urgency"]),
            confidence=float(data["confidence"]),
            consequence_of_drop=float(data["consequence_of_drop"]),
            estimated_compute_cost=float(data["estimated_compute_cost"]),
            rationale=str(data["rationale"]),
            estimator="llm_v1",
            policy_version="v1.0",
            deadline=deadline,
        )
