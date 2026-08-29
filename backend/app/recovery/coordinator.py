"""Failure Recovery Coordinator Service.

Scans stale unacknowledged transport entries, reclaims ownership, reconciles DB idempotency state,
and routes reclaimed messages through the standard LedgerWorker execution pipeline.
"""

from typing import Any
import logging
from datetime import datetime, timezone

from app.config import settings
from app.domain.enums import IdempotencyStatus
from app.domain.models import RecoveryOutcome, QueueMessage, generate_idempotency_key
from app.domain.interfaces import WorkQueueInterface, IdempotencyRepositoryInterface, ExecutionRepositoryInterface
from app.worker.worker import LedgerWorker

logger = logging.getLogger(__name__)


class RecoveryCoordinator:
    """Orchestrates stale pending message discovery, reclamation, and idempotent reprocessing."""

    def __init__(
        self,
        broker: WorkQueueInterface,
        worker: LedgerWorker,
        idempotency_repo: IdempotencyRepositoryInterface | None = None,
        execution_repo: ExecutionRepositoryInterface | None = None,
        worker_pool: Any | None = None,
    ) -> None:
        self._broker = broker
        self._worker = worker
        self._idempotency_repo = idempotency_repo
        self._execution_repo = execution_repo
        self._worker_pool = worker_pool

    async def _get_healthy_worker(self) -> LedgerWorker:
        """Find a healthy non-failed worker instance from pool or default worker."""
        if self._worker_pool and hasattr(self._worker_pool, "workers"):
            for w in self._worker_pool.workers:
                if w._fault_injector:
                    if not await w._fault_injector.is_paused_or_failed(w.worker_id):
                        return w
                else:
                    return w
        return self._worker

    async def run_recovery_scan(
        self,
        min_idle_seconds: float | None = None,
        batch_size: int | None = None,
    ) -> RecoveryOutcome:
        """Execute single recovery scan cycle over transport pending messages.

        Returns:
            RecoveryOutcome containing scan metrics and outcome counts.
        """
        stale_threshold_sec = min_idle_seconds if min_idle_seconds is not None else settings.PENDING_STALE_AFTER_SECONDS
        batch_limit = batch_size if batch_size is not None else settings.RECOVERY_BATCH_SIZE
        min_idle_ms = int(stale_threshold_sec * 1000)

        outcome = RecoveryOutcome()

        # 1. Fetch pending message descriptors for observability
        pending_list = await self._broker.get_pending_messages()
        outcome.scanned_pending_count = len(pending_list)

        if not pending_list:
            return outcome

        # 2. Reclaim stale messages idle longer than threshold
        reclaimed_msgs = await self._broker.claim_stale_messages(
            consumer_name=f"recovery-{self._worker.worker_id}",
            min_idle_ms=min_idle_ms,
            count=batch_limit,
        )
        outcome.stale_candidates_count = len(reclaimed_msgs)
        outcome.reclaimed_count = len(reclaimed_msgs)

        # 3. Route reclaimed messages through a healthy worker processing pipeline
        target_worker = await self._get_healthy_worker()
        for msg in reclaimed_msgs:
            key = generate_idempotency_key(msg.tenant_id, msg.work_item_id, target_worker.action_type)

            # Pre-check DB idempotency state for outcome classification
            if self._idempotency_repo:
                existing = await self._idempotency_repo.get_record(key)
                if existing and existing.status == IdempotencyStatus.COMPLETED:
                    outcome.already_completed_count += 1

            # Determine attempt count from execution repository
            attempt = 1
            if self._execution_repo:
                latest_checkpoint = await self._execution_repo.get_latest_checkpoint(msg.work_item_id)
                if latest_checkpoint:
                    attempt = latest_checkpoint.attempt_number + 1

            # Re-enter healthy worker execution pipeline (idempotency, result persistence, ACK)
            success = await target_worker.process_message(msg, attempt=attempt)
            if success:
                outcome.retried_count += 1
            else:
                outcome.failed_count += 1

        logger.info(
            "Recovery scan completed: scanned=%d, reclaimed=%d, completed_hits=%d",
            outcome.scanned_pending_count,
            outcome.reclaimed_count,
            outcome.already_completed_count,
        )
        return outcome
