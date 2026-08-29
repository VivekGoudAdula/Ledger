"""Idempotency Repository Implementation.

Provides database-enforced atomic ownership claiming using relational composite UNIQUE constraints.
"""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import IdempotencyStatus
from app.domain.models import IdempotencyRecord
from app.domain.interfaces.idempotency import IdempotencyRepositoryInterface
from app.storage.models import IdempotencyRecordORM


class IdempotencyRepository(IdempotencyRepositoryInterface):
    """SQLAlchemy implementation of IdempotencyRepositoryInterface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _ensure_tz(self, dt: datetime | None) -> datetime | None:
        """Ensure naive datetime values are timezone-aware UTC."""
        if dt is None:
            return None
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    def _to_domain(self, orm: IdempotencyRecordORM) -> IdempotencyRecord:
        """Convert ORM model to domain entity."""
        return IdempotencyRecord(
            tenant_id=orm.tenant_id,
            work_item_id=orm.work_item_id,
            action_type=orm.action_type,
            status=IdempotencyStatus(orm.status),
            execution_id=orm.execution_id,
            result_data=orm.result_data or {},
            error_info=orm.error_info,
            created_at=self._ensure_tz(orm.created_at),
            completed_at=self._ensure_tz(orm.completed_at),
        )

    async def claim_ownership(self, record: IdempotencyRecord) -> tuple[bool, IdempotencyRecord]:
        """Attempt atomic ownership claim via DB composite UNIQUE constraint."""
        orm = IdempotencyRecordORM(
            idempotency_key=record.idempotency_key,
            tenant_id=record.tenant_id,
            work_item_id=record.work_item_id,
            action_type=record.action_type,
            status=record.status.value,
            execution_id=record.execution_id,
            result_data=record.result_data,
            error_info=record.error_info,
            created_at=record.created_at,
        )
        try:
            self._session.add(orm)
            await self._session.flush()
            await self._session.commit()
            return True, record
        except IntegrityError:
            await self._session.rollback()
            existing = await self.get_record(record.idempotency_key)
            return False, existing if existing else record

    async def mark_completed(
        self, idempotency_key: str, execution_id: str, result_data: dict[str, Any]
    ) -> bool:
        """Mark idempotency record as COMPLETED."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(IdempotencyRecordORM)
            .where(IdempotencyRecordORM.idempotency_key == idempotency_key)
            .values(
                status=IdempotencyStatus.COMPLETED.value,
                execution_id=execution_id,
                result_data=result_data,
                completed_at=now,
            )
        )
        res = await self._session.execute(stmt)
        await self._session.commit()
        return res.rowcount > 0

    async def mark_failed(
        self, idempotency_key: str, execution_id: str, error_info: str
    ) -> bool:
        """Mark idempotency record as FAILED."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(IdempotencyRecordORM)
            .where(IdempotencyRecordORM.idempotency_key == idempotency_key)
            .values(
                status=IdempotencyStatus.FAILED.value,
                execution_id=execution_id,
                error_info=error_info,
                completed_at=now,
            )
        )
        res = await self._session.execute(stmt)
        await self._session.commit()
        return res.rowcount > 0

    async def get_record(self, idempotency_key: str) -> IdempotencyRecord | None:
        """Fetch idempotency record by key."""
        stmt = select(IdempotencyRecordORM).where(IdempotencyRecordORM.idempotency_key == idempotency_key)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
