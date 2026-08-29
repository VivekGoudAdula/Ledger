"""Admin API Routes for Worker Fault Injection Control Plane.

Provides REST endpoints for querying worker status, pausing/resuming workers,
and injecting/clearing deterministic runtime failure modes.
"""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.fault_injection.models import (
    FailureMode,
    FailureInjectionRequestDTO,
    WorkerControlDTO,
    WorkerStateResponseDTO,
)
from app.fault_injection.service import FaultInjectionService
from app.api.dependencies import get_fault_injector, get_global_worker_pool
from app.worker.pool import WorkerPool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin & Fault Injection"])

KNOWN_WORKERS = {"worker-1", "worker-2", "worker-3", "recovery_worker"}


def _verify_fault_injection_enabled() -> None:
    """Verify that fault injection control plane is enabled in configuration."""
    if not settings.LEDGER_FAULT_INJECTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fault injection control plane is disabled. Enable LEDGER_FAULT_INJECTION_ENABLED=true in config.",
        )


def _validate_worker_id(worker_id: str, pool: WorkerPool | None) -> None:
    """Validate that the worker_id corresponds to a known or pool-registered worker."""
    if pool and pool.get_worker_by_id(worker_id):
        return
    if worker_id in KNOWN_WORKERS:
        return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Worker '{worker_id}' not found in worker pool or registered inventory.",
    )


@router.get("/workers", response_model=WorkerStateResponseDTO)
async def list_workers_state(
    fault_injector: Annotated[FaultInjectionService, Depends(get_fault_injector)],
) -> WorkerStateResponseDTO:
    """Retrieve authoritative backend runtime state for all managed workers."""
    _verify_fault_injection_enabled()
    pool = get_global_worker_pool()

    worker_ids = list(KNOWN_WORKERS)
    if pool:
        for w in pool.workers:
            if w.worker_id not in worker_ids:
                worker_ids.append(w.worker_id)

    snapshots: list[WorkerControlDTO] = []
    for wid in sorted(worker_ids):
        current_task = None
        completed = 0
        failed = 0

        if pool:
            w_inst = pool.get_worker_by_id(wid)
            if w_inst:
                status_obj = w_inst.get_status()
                current_task = status_obj.current_task
                completed = status_obj.tasks_completed
                failed = status_obj.tasks_failed

        control_dto = await fault_injector.get_worker_control_status(
            worker_id=wid,
            current_task=current_task,
            tasks_completed=completed,
            tasks_failed=failed,
        )
        snapshots.append(control_dto)

    return WorkerStateResponseDTO(
        workers=snapshots,
        fault_injection_enabled=settings.LEDGER_FAULT_INJECTION_ENABLED,
    )


@router.post("/workers/{worker_id}/pause", response_model=WorkerControlDTO)
async def pause_worker(
    worker_id: str,
    fault_injector: Annotated[FaultInjectionService, Depends(get_fault_injector)],
) -> WorkerControlDTO:
    """Pause a selected worker so it stops consuming new queue messages while remaining active."""
    _verify_fault_injection_enabled()
    pool = get_global_worker_pool()
    _validate_worker_id(worker_id, pool)

    await fault_injector.pause_worker(worker_id)
    return await fault_injector.get_worker_control_status(worker_id)


@router.post("/workers/{worker_id}/resume", response_model=WorkerControlDTO)
async def resume_worker(
    worker_id: str,
    fault_injector: Annotated[FaultInjectionService, Depends(get_fault_injector)],
) -> WorkerControlDTO:
    """Resume normal execution loop for a paused worker."""
    _verify_fault_injection_enabled()
    pool = get_global_worker_pool()
    _validate_worker_id(worker_id, pool)

    await fault_injector.resume_worker(worker_id)
    return await fault_injector.get_worker_control_status(worker_id)


@router.post("/workers/{worker_id}/inject-failure", response_model=WorkerControlDTO)
async def inject_worker_failure(
    worker_id: str,
    req: FailureInjectionRequestDTO,
    fault_injector: Annotated[FaultInjectionService, Depends(get_fault_injector)],
) -> WorkerControlDTO:
    """Arm a deterministic failure mode at a specific execution lifecycle checkpoint."""
    _verify_fault_injection_enabled()
    pool = get_global_worker_pool()
    _validate_worker_id(worker_id, pool)

    await fault_injector.inject_failure(
        worker_id=worker_id,
        failure_mode=req.failure_mode,
        one_shot=req.one_shot,
    )
    return await fault_injector.get_worker_control_status(worker_id)


@router.post("/workers/{worker_id}/clear-failure", response_model=WorkerControlDTO)
async def clear_worker_failure(
    worker_id: str,
    fault_injector: Annotated[FaultInjectionService, Depends(get_fault_injector)],
) -> WorkerControlDTO:
    """Clear active failure mode and reset worker failure status."""
    _verify_fault_injection_enabled()
    pool = get_global_worker_pool()
    _validate_worker_id(worker_id, pool)

    await fault_injector.clear_failure(worker_id)
    return await fault_injector.get_worker_control_status(worker_id)
