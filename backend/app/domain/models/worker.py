"""Worker Execution Domain Models.

Defines ExecutionCheckpoint, ExecutionResult, and WorkerStatus domain entities.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ExecutionCheckpoint:
    """Represents a durable execution checkpoint created before work task execution."""

    work_item_id: str
    worker_id: str
    attempt_number: int = 1
    state: str = "PROCESSING"
    execution_id: str = field(default_factory=lambda: f"EXEC-{uuid.uuid4().hex[:8]}")
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate checkpoint constraints."""
        if not self.work_item_id or not isinstance(self.work_item_id, str):
            raise ValueError("ExecutionCheckpoint work_item_id must be a non-empty string.")
        if not self.worker_id or not isinstance(self.worker_id, str):
            raise ValueError("ExecutionCheckpoint worker_id must be a non-empty string.")
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be >= 1.")
        if self.started_at and self.started_at.tzinfo is None:
            raise ValueError("started_at timestamp must be timezone-aware.")


@dataclass
class ExecutionResult:
    """Represents durable output state resulting from work task execution."""

    execution_id: str
    work_item_id: str
    status: str  # COMPLETED, FAILED, ALREADY_COMPLETED
    output_data: dict[str, Any] = field(default_factory=dict)
    error_category: str | None = None
    attempt_number: int = 1
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate execution result fields."""
        if not self.execution_id or not isinstance(self.execution_id, str):
            raise ValueError("ExecutionResult execution_id must be a non-empty string.")
        if not self.work_item_id or not isinstance(self.work_item_id, str):
            raise ValueError("ExecutionResult work_item_id must be a non-empty string.")
        if self.status not in ("COMPLETED", "FAILED", "ALREADY_COMPLETED"):
            raise ValueError(f"Invalid ExecutionResult status: '{self.status}'")
        if self.started_at and self.started_at.tzinfo is None:
            raise ValueError("started_at timestamp must be timezone-aware.")
        if self.completed_at and self.completed_at.tzinfo is None:
            raise ValueError("completed_at timestamp must be timezone-aware.")


@dataclass
class WorkerStatus:
    """Telemetry status representing active worker health and task metrics."""

    worker_id: str
    state: str = "READY"  # STARTING, READY, PROCESSING, STOPPING, STOPPED, FAILED
    current_task: str | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
