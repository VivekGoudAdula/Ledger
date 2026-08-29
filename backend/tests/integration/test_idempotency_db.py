"""Integration Tests for Database-Enforced Idempotency Repository.

Validates composite UNIQUE (tenant_id, work_item_id, action_type) constraint enforcement and multi-tenant isolation.
"""

import pytest

from app.domain.enums import IdempotencyStatus
from app.domain.models import IdempotencyRecord
from app.storage.repositories import IdempotencyRepository


@pytest.mark.asyncio
async def test_db_composite_unique_constraint_enforced(db_session):
    repo = IdempotencyRepository(db_session)

    rec1 = IdempotencyRecord(
        tenant_id="t_db",
        work_item_id="item_db_1",
        action_type="ANALYZE_SIGNAL",
        status=IdempotencyStatus.IN_PROGRESS,
    )
    claimed1, _ = await repo.claim_ownership(rec1)
    assert claimed1 is True

    # Mark completed
    await repo.mark_completed(rec1.idempotency_key, "EXEC-1", {"status": "done"})

    # Duplicate claim attempt for same tenant + work_item_id + action_type
    rec2 = IdempotencyRecord(
        tenant_id="t_db",
        work_item_id="item_db_1",
        action_type="ANALYZE_SIGNAL",
        status=IdempotencyStatus.IN_PROGRESS,
    )
    claimed2, existing = await repo.claim_ownership(rec2)
    assert claimed2 is False
    assert existing.status == IdempotencyStatus.COMPLETED
    assert existing.result_data == {"status": "done"}


@pytest.mark.asyncio
async def test_multi_tenant_idempotency_namespace_isolation(db_session):
    repo = IdempotencyRepository(db_session)

    # Tenant A
    rec_a = IdempotencyRecord(
        tenant_id="tenant_a",
        work_item_id="shared_item",
        action_type="ANALYZE_SIGNAL",
    )
    claimed_a, _ = await repo.claim_ownership(rec_a)
    assert claimed_a is True

    # Tenant B (Same work_item_id and action_type!)
    rec_b = IdempotencyRecord(
        tenant_id="tenant_b",
        work_item_id="shared_item",
        action_type="ANALYZE_SIGNAL",
    )
    claimed_b, _ = await repo.claim_ownership(rec_b)
    assert claimed_b is True  # Allowed due to multi-tenant isolation!
