"""Valuation Repository Implementation.

Implements ValuationRepositoryInterface for persisting and querying ValueAssessment records.
"""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ValueAssessment
from app.domain.interfaces.repositories import ValuationRepositoryInterface
from app.storage.models import ValueAssessmentORM


class ValuationRepository(ValuationRepositoryInterface):
    """SQLAlchemy implementation of ValuationRepositoryInterface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _ensure_tz(self, dt: datetime | None) -> datetime | None:
        """Ensure datetime object is timezone-aware (UTC)."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    async def save_assessment(self, assessment: ValueAssessment) -> ValueAssessment:
        """Persist a ValueAssessment record."""
        orm = ValueAssessmentORM(
            assessment_id=assessment.assessment_id,
            work_item_id=assessment.work_item_id,
            work_item_type=assessment.work_item_type,
            urgency=assessment.urgency,
            confidence=assessment.confidence,
            consequence_of_drop=assessment.consequence_of_drop,
            estimated_compute_cost=assessment.estimated_compute_cost,
            expected_value=assessment.expected_value,
            value_per_compute=assessment.value_per_compute,
            rationale=assessment.rationale,
            estimator=assessment.estimator,
            policy_version=assessment.policy_version,
            is_fallback=assessment.is_fallback,
            deadline=self._ensure_tz(assessment.deadline),
            estimated_at=self._ensure_tz(assessment.estimated_at),
        )
        self._session.add(orm)
        await self._session.flush()
        return assessment

    async def get_latest_assessment(self, work_item_id: str) -> ValueAssessment | None:
        """Fetch latest ValueAssessment by work_item_id."""
        stmt = (
            select(ValueAssessmentORM)
            .where(ValueAssessmentORM.work_item_id == work_item_id)
            .order_by(ValueAssessmentORM.estimated_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None

        return ValueAssessment(
            assessment_id=orm.assessment_id,
            work_item_id=orm.work_item_id,
            work_item_type=orm.work_item_type,
            urgency=orm.urgency,
            confidence=orm.confidence,
            consequence_of_drop=orm.consequence_of_drop,
            estimated_compute_cost=orm.estimated_compute_cost,
            expected_value=orm.expected_value,
            value_per_compute=orm.value_per_compute,
            rationale=orm.rationale,
            estimator=orm.estimator,
            policy_version=orm.policy_version,
            is_fallback=orm.is_fallback,
            deadline=self._ensure_tz(orm.deadline),
            estimated_at=self._ensure_tz(orm.estimated_at),
        )
