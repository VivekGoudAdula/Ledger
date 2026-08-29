"""ExecutionResult Domain Entity.

Represents the output of worker action execution.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ExecutionResult:
    """Outcome of worker action execution."""

    event_id: str
    worker_id: str
    success: bool
    output: dict[str, Any]
    error_message: str | None = None
    execution_duration_ms: float = 0.0
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
