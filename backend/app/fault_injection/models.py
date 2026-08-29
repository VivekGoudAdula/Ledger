"""Fault Injection Domain Models and Enums.

Defines supported failure modes, worker states, custom exception types,
and request/response DTOs for the fault injection control plane.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class WorkerState(str, Enum):
    """Authoritative backend worker execution lifecycle states."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"


class FailureMode(str, Enum):
    """Deterministic failure injection execution points."""

    BEFORE_EXECUTION = "before_execution"
    DURING_EXECUTION = "during_execution"
    AFTER_EXECUTION_BEFORE_ACK = "after_execution_before_ack"


class WorkerFaultInjectionError(Exception):
    """Custom exception raised when a worker hits an active fault injection point."""

    def __init__(self, message: str, worker_id: str, failure_mode: FailureMode) -> None:
        super().__init__(message)
        self.worker_id = worker_id
        self.failure_mode = failure_mode


class FailureInjectionRequestDTO(BaseModel):
    """Request payload for configuring worker fault injection."""

    failure_mode: FailureMode = Field(..., description="Target execution checkpoint for deterministic failure.")
    one_shot: bool = Field(default=True, description="Whether failure triggers once then auto-clears.")


class WorkerControlDTO(BaseModel):
    """Worker operational status snapshot."""

    worker_id: str = Field(..., description="Unique worker identifier.")
    state: WorkerState = Field(..., description="Backend-derived state.")
    is_paused: bool = Field(default=False, description="Whether worker pause is active.")
    active_failure_mode: Optional[FailureMode] = Field(default=None, description="Currently configured failure mode.")
    one_shot: bool = Field(default=True, description="Whether active failure mode auto-clears after 1 hit.")
    failure_count: int = Field(default=0, description="Total injected failures triggered.")
    current_task: Optional[str] = Field(default=None, description="Current work item ID being processed.")
    tasks_completed: int = Field(default=0, description="Tasks completed successfully.")
    tasks_failed: int = Field(default=0, description="Tasks failed.")


class WorkerStateResponseDTO(BaseModel):
    """API response container for worker pool state."""

    workers: list[WorkerControlDTO] = Field(default_factory=list, description="List of worker statuses.")
    fault_injection_enabled: bool = Field(..., description="Whether fault injection control plane is active.")
