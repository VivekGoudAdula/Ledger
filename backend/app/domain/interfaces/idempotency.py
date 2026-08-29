"""Idempotency Repository Interface Protocol.

Defines protocol for atomic ownership claiming and idempotency record persistence.
"""

from typing import Protocol, runtime_checkable, Any
from app.domain.models import IdempotencyRecord


@runtime_checkable
class IdempotencyRepositoryInterface(Protocol):
    """Protocol interface for atomic idempotency record claim and lifecycle updates."""

    async def claim_ownership(
        self, record: IdempotencyRecord
    ) -> tuple[bool, IdempotencyRecord]:
        """Attempt atomic ownership claim via database uniqueness constraint.

        Returns:
            Tuple of (claimed_success: bool, record: IdempotencyRecord)
            If claimed_success is False, record contains the existing record (COMPLETED/IN_PROGRESS).
        """
        ...

    async def mark_completed(
        self, idempotency_key: str, execution_id: str, result_data: dict[str, Any]
    ) -> bool:
        """Mark idempotency record as COMPLETED with durable output data."""
        ...

    async def mark_failed(
        self, idempotency_key: str, execution_id: str, error_info: str
    ) -> bool:
        """Mark idempotency record as FAILED."""
        ...

    async def get_record(self, idempotency_key: str) -> IdempotencyRecord | None:
        """Fetch idempotency record by primary key."""
        ...
