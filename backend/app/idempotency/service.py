"""Idempotency Application Service.

Orchestrates atomic logical ownership claims, completion marking, and result retrieval.
"""

from typing import Any
import logging

from app.domain.enums import IdempotencyStatus, ActionType
from app.domain.models import IdempotencyRecord, generate_idempotency_key
from app.domain.interfaces.idempotency import IdempotencyRepositoryInterface

logger = logging.getLogger(__name__)


class IdempotencyService:
    """Application service managing database-enforced execution idempotency."""

    def __init__(self, repository: IdempotencyRepositoryInterface) -> None:
        self._repo = repository

    async def claim_execution_ownership(
        self,
        tenant_id: str,
        work_item_id: str,
        action_type: str | ActionType,
        execution_id: str | None = None,
    ) -> tuple[bool, IdempotencyRecord]:
        """Attempt atomic ownership claim for logical action over work item.

        Returns:
            Tuple of (claimed_success: bool, record: IdempotencyRecord)
            If claimed_success is False, record contains existing status (COMPLETED/IN_PROGRESS).
        """
        act_str = action_type.value if isinstance(action_type, ActionType) else str(action_type)
        record = IdempotencyRecord(
            tenant_id=tenant_id,
            work_item_id=work_item_id,
            action_type=act_str,
            status=IdempotencyStatus.IN_PROGRESS,
            execution_id=execution_id,
        )

        claimed, final_record = await self._repo.claim_ownership(record)
        if not claimed:
            logger.info(
                "Idempotency Guard HIT: key='%s', status='%s'",
                final_record.idempotency_key,
                final_record.status.value,
            )
        return claimed, final_record

    async def complete_execution(
        self,
        tenant_id: str,
        work_item_id: str,
        action_type: str | ActionType,
        execution_id: str,
        result_data: dict[str, Any],
    ) -> bool:
        """Mark logical action execution as COMPLETED."""
        key = generate_idempotency_key(tenant_id, work_item_id, action_type)
        return await self._repo.mark_completed(key, execution_id, result_data)

    async def fail_execution(
        self,
        tenant_id: str,
        work_item_id: str,
        action_type: str | ActionType,
        execution_id: str,
        error_info: str,
    ) -> bool:
        """Mark logical action execution as FAILED."""
        key = generate_idempotency_key(tenant_id, work_item_id, action_type)
        return await self._repo.mark_failed(key, execution_id, error_info)
