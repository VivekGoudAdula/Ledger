"""Execution Repository Implementation.

Provides durable SQLite persistence for ExecutionCheckpoint and ExecutionResult entities.
"""

from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ExecutionCheckpoint, ExecutionResult
from app.domain.interfaces.execution import ExecutionRepositoryInterface
from app.storage.models import ExecutionCheckpointORM, ExecutionResultORM


class ExecutionRepository(ExecutionRepositoryInterface):
    """Repository handling persistence of worker execution checkpoints and results."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _ensure_tz(self, dt: datetime | None) -> datetime | None:
        """Ensure naive database datetime values are timezone-aware UTC."""
        if dt is None:
            return None
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    async def save_checkpoint(self, checkpoint: ExecutionCheckpoint) -> ExecutionCheckpoint:
        """Save worker execution checkpoint to database."""
        orm = ExecutionCheckpointORM(
            execution_id=checkpoint.execution_id,
            work_item_id=checkpoint.work_item_id,
            worker_id=checkpoint.worker_id,
            attempt_number=checkpoint.attempt_number,
            state=checkpoint.state,
            started_at=checkpoint.started_at,
        )
        self._session.add(orm)
        await self._session.commit()
        return checkpoint

    async def get_latest_checkpoint(self, work_item_id: str) -> ExecutionCheckpoint | None:
        """Retrieve latest execution checkpoint for work item."""
        stmt = (
            select(ExecutionCheckpointORM)
            .where(ExecutionCheckpointORM.work_item_id == work_item_id)
            .order_by(desc(ExecutionCheckpointORM.started_at))
            .limit(1)
        )
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        if not orm:
            return None

        return ExecutionCheckpoint(
            execution_id=orm.execution_id,
            work_item_id=orm.work_item_id,
            worker_id=orm.worker_id,
            attempt_number=orm.attempt_number,
            state=orm.state,
            started_at=self._ensure_tz(orm.started_at),
        )

    async def save_result(self, result: ExecutionResult) -> ExecutionResult:
        """Save durable execution result to database."""
        orm = ExecutionResultORM(
            execution_id=result.execution_id,
            work_item_id=result.work_item_id,
            status=result.status,
            output_data=result.output_data,
            error_category=result.error_category,
            attempt_number=result.attempt_number,
            started_at=result.started_at,
            completed_at=result.completed_at,
        )
        self._session.add(orm)
        await self._session.commit()
        return result

    async def get_result_by_work_item(self, work_item_id: str) -> ExecutionResult | None:
        """Retrieve completed execution result for work item if existing."""
        stmt = select(ExecutionResultORM).where(ExecutionResultORM.work_item_id == work_item_id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        if not orm:
            return None

        return ExecutionResult(
            execution_id=orm.execution_id,
            work_item_id=orm.work_item_id,
            status=orm.status,
            output_data=orm.output_data,
            error_category=orm.error_category,
            attempt_number=orm.attempt_number,
            started_at=self._ensure_tz(orm.started_at),
            completed_at=self._ensure_tz(orm.completed_at),
        )
