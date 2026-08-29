"""Action Executor Interface Protocol.

Interface for executing actions triggered by admitted work.
"""

from typing import Protocol
from app.domain.models import SignalEvent, ExecutionResult


class ActionExecutorInterface(Protocol):
    """Protocol for executing work actions."""

    async def execute(self, event: SignalEvent, worker_id: str) -> ExecutionResult:
        """Execute action associated with the signal event."""
        ...
