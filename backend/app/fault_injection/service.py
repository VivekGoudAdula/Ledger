"""Fault Injection Control Service.

Manages deterministic failure mode state, worker pause state, and fault triggers
for Ledger worker instances in a thread-safe / async-safe manner.
"""

import asyncio
import logging
from typing import Dict, Optional, Set

from app.fault_injection.models import (
    FailureMode,
    WorkerState,
    WorkerFaultInjectionError,
    WorkerControlDTO,
)

logger = logging.getLogger(__name__)


class FaultInjectionService:
    """Service governing runtime fault injection and pause state per worker."""

    def __init__(self) -> None:
        self._paused_workers: Set[str] = set()
        self._active_failures: Dict[str, FailureMode] = {}
        self._one_shot_flags: Dict[str, bool] = {}
        self._failure_counts: Dict[str, int] = {}
        self._failed_workers: Dict[str, str] = {}  # worker_id -> reason
        self._lock = asyncio.Lock()

    async def pause_worker(self, worker_id: str) -> None:
        """Pause a worker so it stops consuming new queue items."""
        async with self._lock:
            self._paused_workers.add(worker_id)
            logger.info("FaultInjectionService: Worker [%s] PAUSED", worker_id)

    async def resume_worker(self, worker_id: str) -> None:
        """Resume a worker so it resumes consuming queue items."""
        async with self._lock:
            self._paused_workers.discard(worker_id)
            self._failed_workers.pop(worker_id, None)
            logger.info("FaultInjectionService: Worker [%s] RESUMED", worker_id)

    async def inject_failure(self, worker_id: str, failure_mode: FailureMode, one_shot: bool = True) -> None:
        """Arm a deterministic failure mode for a target worker."""
        async with self._lock:
            self._active_failures[worker_id] = failure_mode
            self._one_shot_flags[worker_id] = one_shot
            logger.info("FaultInjectionService: Worker [%s] armed with failure mode '%s' (one_shot=%s)", worker_id, failure_mode.value, one_shot)

    async def clear_failure(self, worker_id: str) -> None:
        """Clear armed failure mode and failed status for a target worker."""
        async with self._lock:
            self._active_failures.pop(worker_id, None)
            self._one_shot_flags.pop(worker_id, None)
            self._failed_workers.pop(worker_id, None)
            logger.info("FaultInjectionService: Worker [%s] failure mode cleared", worker_id)

    async def is_paused(self, worker_id: str) -> bool:
        """Check if target worker is explicitly paused."""
        async with self._lock:
            return worker_id in self._paused_workers

    async def is_failed(self, worker_id: str) -> bool:
        """Check if target worker is currently in a FAILED state."""
        async with self._lock:
            return worker_id in self._failed_workers

    async def is_paused_or_failed(self, worker_id: str) -> bool:
        """Check if target worker is paused or failed (ineligible to process new queue work)."""
        async with self._lock:
            return worker_id in self._paused_workers or worker_id in self._failed_workers

    async def get_active_failure_mode(self, worker_id: str) -> Optional[FailureMode]:
        """Get target worker's active failure mode if armed."""
        async with self._lock:
            return self._active_failures.get(worker_id)

    async def check_and_trigger_fault(self, worker_id: str, current_checkpoint: FailureMode) -> None:
        """Check if target worker has an active fault matching the current execution checkpoint.
        
        If matched, raises WorkerFaultInjectionError and clears one-shot faults.
        """
        mode_to_trigger: Optional[FailureMode] = None
        async with self._lock:
            active_mode = self._active_failures.get(worker_id)
            if active_mode == current_checkpoint:
                mode_to_trigger = active_mode
                self._failure_counts[worker_id] = self._failure_counts.get(worker_id, 0) + 1
                self._failed_workers[worker_id] = f"Fault injected at {current_checkpoint.value}"
                if self._one_shot_flags.get(worker_id, True):
                    self._active_failures.pop(worker_id, None)
                    self._one_shot_flags.pop(worker_id, None)

        if mode_to_trigger:
            logger.warning("Worker [%s] FAULT TRIGGERED at checkpoint '%s'", worker_id, current_checkpoint.value)
            raise WorkerFaultInjectionError(
                message=f"Injected fault at checkpoint '{current_checkpoint.value}'",
                worker_id=worker_id,
                failure_mode=mode_to_trigger,
            )

    async def get_worker_control_status(
        self,
        worker_id: str,
        current_task: Optional[str] = None,
        tasks_completed: int = 0,
        tasks_failed: int = 0,
        is_recovering: bool = False,
    ) -> WorkerControlDTO:
        """Derive authoritative backend worker state snapshot."""
        async with self._lock:
            is_paused = worker_id in self._paused_workers
            has_failed = worker_id in self._failed_workers
            active_mode = self._active_failures.get(worker_id)
            one_shot = self._one_shot_flags.get(worker_id, True)
            failure_cnt = self._failure_counts.get(worker_id, 0)

            if is_paused:
                state = WorkerState.PAUSED
            elif has_failed:
                state = WorkerState.FAILED
            elif is_recovering:
                state = WorkerState.RECOVERING
            else:
                state = WorkerState.RUNNING

            return WorkerControlDTO(
                worker_id=worker_id,
                state=state,
                is_paused=is_paused,
                active_failure_mode=active_mode,
                one_shot=one_shot,
                failure_count=failure_cnt,
                current_task=current_task,
                tasks_completed=tasks_completed,
                tasks_failed=tasks_failed + failure_cnt,
            )
