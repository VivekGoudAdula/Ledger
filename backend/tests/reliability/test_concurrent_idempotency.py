"""Reliability Concurrency Tests for Database-Enforced Idempotency.

Launches concurrent ownership claim attempts against the database for the exact same logical operation,
verifying that the composite UNIQUE constraint enforces EXACTLY ONE owner.
"""

import asyncio
import pytest

from app.domain.enums import IdempotencyStatus
from app.domain.models import IdempotencyRecord
from app.storage.repositories import IdempotencyRepository


@pytest.mark.asyncio
async def test_concurrent_idempotency_race_protection(test_session_factory):
    # Launch 10 concurrent workers attempting to claim the exact same idempotency key
    async def _try_claim(worker_idx: int) -> tuple[bool, str]:
        async with test_session_factory() as session:
            repo = IdempotencyRepository(session)
            rec = IdempotencyRecord(
                tenant_id="tenant_race",
                work_item_id="item_race_999",
                action_type="ANALYZE_SIGNAL",
                execution_id=f"EXEC-WORKER-{worker_idx}",
            )
            claimed, final_rec = await repo.claim_ownership(rec)
            return claimed, final_rec.execution_id or ""

    results = await asyncio.gather(*[_try_claim(i) for i in range(10)])

    claimed_count = sum(1 for claimed, _ in results if claimed)
    failed_count = sum(1 for claimed, _ in results if not claimed)

    # EXACTLY ONE worker MUST win the atomic claim!
    assert claimed_count == 1
    assert failed_count == 9
