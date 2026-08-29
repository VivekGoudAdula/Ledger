"""Unit Tests for IdempotencyService.

Validates application service ownership claims and completion updates.
"""

from datetime import datetime, timezone
import pytest

from app.domain.enums import IdempotencyStatus, ActionType
from app.domain.models import IdempotencyRecord
from app.storage.repositories import IdempotencyRepository
from app.idempotency.service import IdempotencyService


@pytest.mark.asyncio
async def test_idempotency_service_claim_and_complete(db_session):
    repo = IdempotencyRepository(db_session)
    service = IdempotencyService(repository=repo)

    # Claim ownership
    claimed, rec = await service.claim_execution_ownership(
        tenant_id="t_serv",
        work_item_id="item_serv_1",
        action_type=ActionType.ANALYZE_SIGNAL,
        execution_id="EXEC-SERV-1",
    )
    assert claimed is True
    assert rec.status == IdempotencyStatus.IN_PROGRESS

    # Complete execution
    completed = await service.complete_execution(
        tenant_id="t_serv",
        work_item_id="item_serv_1",
        action_type=ActionType.ANALYZE_SIGNAL,
        execution_id="EXEC-SERV-1",
        result_data={"result": "success"},
    )
    assert completed is True

    # Duplicate claim attempt
    claimed2, rec2 = await service.claim_execution_ownership(
        tenant_id="t_serv",
        work_item_id="item_serv_1",
        action_type=ActionType.ANALYZE_SIGNAL,
        execution_id="EXEC-SERV-2",
    )
    assert claimed2 is False
    assert rec2.status == IdempotencyStatus.COMPLETED
