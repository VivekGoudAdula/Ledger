"""Idempotency Domain Model.

Defines IdempotencyRecord entity and key generation helper functions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.enums import IdempotencyStatus, ActionType


def generate_idempotency_key(tenant_id: str, work_item_id: str, action_type: str | ActionType) -> str:
    """Generate canonical idempotency key in format: tenant_id:work_item_id:action_type."""
    if not tenant_id or not isinstance(tenant_id, str):
        raise ValueError("tenant_id must be a non-empty string.")
    if not work_item_id or not isinstance(work_item_id, str):
        raise ValueError("work_item_id must be a non-empty string.")

    act_str = action_type.value if isinstance(action_type, ActionType) else str(action_type)
    if not act_str:
        raise ValueError("action_type must be a non-empty string.")

    return f"{tenant_id}:{work_item_id}:{act_str}"


@dataclass
class IdempotencyRecord:
    """Durable idempotency record protecting against duplicate logical executions."""

    tenant_id: str
    work_item_id: str
    action_type: str
    idempotency_key: str = field(init=False)
    status: IdempotencyStatus = IdempotencyStatus.IN_PROGRESS
    execution_id: str | None = None
    result_data: dict[str, Any] = field(default_factory=dict)
    error_info: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Compute key and validate timezone awareness."""
        self.idempotency_key = generate_idempotency_key(
            tenant_id=self.tenant_id,
            work_item_id=self.work_item_id,
            action_type=self.action_type,
        )
        if self.created_at and self.created_at.tzinfo is None:
            raise ValueError("created_at timestamp must be timezone-aware.")
        if self.completed_at and self.completed_at.tzinfo is None:
            raise ValueError("completed_at timestamp must be timezone-aware.")
