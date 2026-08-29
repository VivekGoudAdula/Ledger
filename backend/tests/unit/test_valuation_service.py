"""Unit Tests for ValueEstimationService.

Validates primary vs fallback estimator execution, timeout protection,
derived value calculation, and persistence.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.domain.models import SignalEvent
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.valuation.ai_estimator import LLMValueEstimator
from app.valuation.service import ValueEstimationService
from app.storage.repositories import ValuationRepository, EventRepository


@pytest.mark.asyncio
async def test_valuation_service_rule_based_mode(db_session):
    event_repo = EventRepository(db_session)
    val_repo = ValuationRepository(db_session)

    event = SignalEvent(
        source_type="github",
        source_id="1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        event_type="test_event",
        raw_payload={"test": "payload"},
    )
    await event_repo.save(event)

    service = ValueEstimationService(repository=val_repo, mode="rule_based")
    assessment = await service.assess_work_item(event)

    assert assessment.work_item_id == event.event_id
    assert assessment.is_fallback is False
    assert assessment.expected_value > 0.0
    assert assessment.value_per_compute > 0.0

    # Verify persistence
    saved = await val_repo.get_latest_assessment(event.event_id)
    assert saved is not None
    assert saved.assessment_id == assessment.assessment_id


@pytest.mark.asyncio
async def test_valuation_service_ai_failure_triggers_fallback(db_session):
    val_repo = ValuationRepository(db_session)

    event = SignalEvent(
        source_type="github",
        source_id="2",
        tenant_id="t1",
        payload_hash="b" * 64,
        coalesce_key="k2",
        event_type="test_event",
        raw_payload={"test": "payload"},
    )

    # Primary LLM estimator mocked to raise exception
    failing_ai_estimator = MagicMock(spec=LLMValueEstimator)
    failing_ai_estimator.estimate = AsyncMock(side_effect=RuntimeError("LLM API Timeout"))

    service = ValueEstimationService(
        estimator=failing_ai_estimator,
        repository=val_repo,
        mode="llm_with_fallback",
    )

    assessment = await service.assess_work_item(event)
    assert assessment.is_fallback is True
    assert assessment.estimator == "rule_based_fallback"
    assert "FALLBACK" in assessment.rationale
    assert assessment.expected_value > 0.0
