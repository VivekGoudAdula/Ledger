"""Value Estimation Application Service.

Orchestrates work item value estimation, mode handling, AI fallback protection,
deterministic derived value calculations, and persistence.
"""

import asyncio
import logging
from typing import Literal

from app.config import settings
from app.domain.models import SignalEvent, CoalescedIncident, ValueAssessment
from app.domain.interfaces.estimator import ValueEstimatorInterface
from app.domain.interfaces.repositories import ValuationRepositoryInterface
from app.valuation.rule_estimator import RuleBasedValueEstimator

logger = logging.getLogger(__name__)


class ValueEstimationService:
    """Service managing work item valuation, AI timeouts, fallback, and calculation rules."""

    def __init__(
        self,
        estimator: ValueEstimatorInterface | None = None,
        fallback_estimator: RuleBasedValueEstimator | None = None,
        repository: ValuationRepositoryInterface | None = None,
        mode: Literal["rule_based", "llm", "llm_with_fallback"] | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._fallback_estimator = fallback_estimator or RuleBasedValueEstimator()
        self._primary_estimator = estimator or self._fallback_estimator
        self._repository = repository
        self._mode = mode or settings.VALUE_ESTIMATOR_MODE
        self._timeout = timeout_seconds or settings.AI_ESTIMATOR_TIMEOUT_SECONDS

    async def assess_work_item(
        self, work_item: SignalEvent | CoalescedIncident
    ) -> ValueAssessment:
        """Estimate work item value dimensions and compute derived expected value and value_per_compute."""
        assessment: ValueAssessment | None = None

        if self._mode == "rule_based":
            assessment = await self._fallback_estimator.estimate(work_item)
        else:
            try:
                # Attempt primary estimator under strict timeout
                assessment = await asyncio.wait_for(
                    self._primary_estimator.estimate(work_item),
                    timeout=self._timeout,
                )
            except Exception as exc:
                if self._mode == "llm_with_fallback":
                    logger.warning("AI estimator failed (%s: %s). Triggering rule-based fallback.", type(exc).__name__, exc)
                    assessment = await self._fallback_estimator.estimate(work_item)
                    assessment.is_fallback = True
                    assessment.estimator = "rule_based_fallback"
                    assessment.rationale = f"[FALLBACK ({type(exc).__name__})]: {assessment.rationale}"
                else:
                    raise

        # Step 2: Compute deterministic derived values (Expected Value & Value Per Compute)
        created_at = work_item.created_at if isinstance(work_item, SignalEvent) else work_item.first_seen
        deadline = work_item.deadline_at if isinstance(work_item, SignalEvent) else None

        expected_val = ValueAssessment.compute_expected_value(
            urgency=assessment.urgency,
            confidence=assessment.confidence,
            consequence_of_drop=assessment.consequence_of_drop,
            deadline=deadline,
            created_at=created_at,
        )

        value_per_comp = ValueAssessment.compute_value_per_compute(
            expected_value=expected_val,
            estimated_compute_cost=assessment.estimated_compute_cost,
        )

        assessment.expected_value = expected_val
        assessment.value_per_compute = value_per_comp

        # Step 3: Persist assessment if repository available
        if self._repository:
            try:
                await self._repository.save_assessment(assessment)
            except Exception as repo_exc:
                logger.error("Failed to persist ValueAssessment: %s", repo_exc)

        return assessment
