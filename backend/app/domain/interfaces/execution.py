"""Execution Interfaces Protocol.

Defines protocols for deterministic task execution handlers and execution state persistence repositories.
"""

from typing import Protocol, runtime_checkable, Any
from app.domain.models import (
    SignalEvent,
    CoalescedIncident,
    ValueAssessment,
    ExecutionCheckpoint,
    ExecutionResult,
)


@runtime_checkable
class ExecutionHandlerInterface(Protocol):
    """Protocol interface for task execution handlers processing admitted work."""

    async def execute(
        self,
        work_item: SignalEvent | CoalescedIncident,
        assessment: ValueAssessment | None = None,
    ) -> dict[str, Any]:
        """Execute deterministic business analysis or operation over work item."""
        ...


@runtime_checkable
class ExecutionRepositoryInterface(Protocol):
    """Protocol interface for execution checkpoints and results persistence."""

    async def save_checkpoint(self, checkpoint: ExecutionCheckpoint) -> ExecutionCheckpoint:
        """Save execution checkpoint record."""
        ...

    async def get_latest_checkpoint(self, work_item_id: str) -> ExecutionCheckpoint | None:
        """Retrieve latest execution checkpoint for work item."""
        ...

    async def save_result(self, result: ExecutionResult) -> ExecutionResult:
        """Save durable execution result record."""
        ...

    async def get_result_by_work_item(self, work_item_id: str) -> ExecutionResult | None:
        """Retrieve completed execution result for work item if existing."""
        ...
