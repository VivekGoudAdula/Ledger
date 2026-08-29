"""Ledger Worker Core Engine.

Consumes admitted work from WorkQueueInterface, validates messages, enforces database idempotency,
creates execution checkpoints, executes tasks with timeouts, persists results, and ACKs on completion.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any

from app.config import settings
from app.domain.enums import EventStatus, IdempotencyStatus, ActionType
from app.domain.models import (
    QueueMessage,
    ExecutionCheckpoint,
    ExecutionResult,
    WorkerStatus,
    IdempotencyRecord,
    generate_idempotency_key,
)
from app.domain.interfaces import (
    WorkQueueInterface,
    EventRepositoryInterface,
    ExecutionRepositoryInterface,
    ExecutionHandlerInterface,
    IdempotencyRepositoryInterface,
)
from app.worker.retry_policy import RetryPolicy
from app.worker.handler import DeterministicExecutionHandler

logger = logging.getLogger(__name__)


class LedgerWorker:
    """Core worker process executing admitted work items reliably with bounded retries."""

    def __init__(
        self,
        worker_id: str,
        broker: WorkQueueInterface,
        event_repo: EventRepositoryInterface,
        execution_repo: ExecutionRepositoryInterface,
        idempotency_repo: IdempotencyRepositoryInterface | None = None,
        handler: ExecutionHandlerInterface | None = None,
        retry_policy: RetryPolicy | None = None,
        max_concurrency: int = 4,
        timeout_seconds: float = 30.0,
        action_type: str = "ANALYZE_SIGNAL",
    ) -> None:
        self.worker_id = worker_id
        self._broker = broker
        self._event_repo = event_repo
        self._execution_repo = execution_repo
        self._idempotency_repo = idempotency_repo
        self._handler = handler or DeterministicExecutionHandler()
        self._retry_policy = retry_policy or RetryPolicy()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._timeout_seconds = timeout_seconds
        self.action_type = action_type

        self._running = False
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._current_task: str | None = None
        self._started_at = datetime.now(timezone.utc)
        self._last_activity = datetime.now(timezone.utc)

    def get_status(self) -> WorkerStatus:
        """Retrieve current worker health telemetry."""
        state = "RUNNING" if self._running else "STOPPED"
        return WorkerStatus(
            worker_id=self.worker_id,
            state=state,
            current_task=self._current_task,
            tasks_completed=self._tasks_completed,
            tasks_failed=self._tasks_failed,
            last_activity=self._last_activity,
            started_at=self._started_at,
        )

    async def process_message(self, msg: QueueMessage, attempt: int = 1) -> bool:
        """Execute single queue message with validation, DB idempotency claims, checkpointing, and ACKs."""
        async with self._semaphore:
            self._current_task = msg.work_item_id
            self._last_activity = datetime.now(timezone.utc)
            start_time = datetime.now(timezone.utc)

            # 1. Message Contract Validation
            if msg.schema_version != 1 or not msg.work_item_id or not msg.tenant_id:
                logger.error("Worker [%s] rejected malformed QueueMessage: %s", self.worker_id, msg)
                self._tasks_failed += 1
                self._current_task = None
                return False

            # 2. Database-Enforced Idempotency Atomic Ownership Claim
            idempotency_key = generate_idempotency_key(msg.tenant_id, msg.work_item_id, self.action_type)
            if self._idempotency_repo:
                claim_rec = IdempotencyRecord(
                    tenant_id=msg.tenant_id,
                    work_item_id=msg.work_item_id,
                    action_type=self.action_type,
                    status=IdempotencyStatus.IN_PROGRESS,
                )
                claimed, existing = await self._idempotency_repo.claim_ownership(claim_rec)
                if not claimed:
                    if existing.status == IdempotencyStatus.COMPLETED:
                        logger.info("Worker [%s] IDEMPOTENCY HIT for '%s' - already COMPLETED. Safely ACKing message.", self.worker_id, idempotency_key)
                        if msg.transport_id:
                            await self._broker.acknowledge(msg.transport_id)
                        self._tasks_completed += 1
                        self._current_task = None
                        return True
                    elif existing.status == IdempotencyStatus.IN_PROGRESS and attempt == 1:
                        logger.info("Worker [%s] DUPLICATE IN_PROGRESS for '%s'. Skipping duplicate execution.", self.worker_id, idempotency_key)
                        self._current_task = None
                        return False

            # 3. Idempotency Check via ExecutionRepository Fallback
            existing_result = await self._execution_repo.get_result_by_work_item(msg.work_item_id)
            if existing_result and existing_result.status in ("COMPLETED", "ALREADY_COMPLETED"):
                logger.info("Worker [%s] skipping already completed work item '%s'", self.worker_id, msg.work_item_id)
                if msg.transport_id:
                    await self._broker.acknowledge(msg.transport_id)
                self._tasks_completed += 1
                self._current_task = None
                return True

            # 4. Load Authoritative State from Database
            work_item = await self._event_repo.get_by_id(msg.work_item_id)
            if not work_item:
                logger.error("Worker [%s] work item '%s' not found in store", self.worker_id, msg.work_item_id)
                self._tasks_failed += 1
                self._current_task = None
                return False

            # 5. State Transition & Durable Checkpoint
            await self._event_repo.update_status(msg.work_item_id, EventStatus.PROCESSING)
            checkpoint = ExecutionCheckpoint(
                work_item_id=msg.work_item_id,
                worker_id=self.worker_id,
                attempt_number=attempt,
                state="PROCESSING",
                started_at=start_time,
            )
            await self._execution_repo.save_checkpoint(checkpoint)

            # 6. Task Execution with Timeout & Exception Handling
            try:
                output = await asyncio.wait_for(
                    self._handler.execute(work_item),
                    timeout=self._timeout_seconds,
                )
                end_time = datetime.now(timezone.utc)

                # 7. Durable Result Persistence & Idempotency Mark Completed
                result = ExecutionResult(
                    execution_id=checkpoint.execution_id,
                    work_item_id=msg.work_item_id,
                    status="COMPLETED",
                    output_data=output,
                    attempt_number=attempt,
                    started_at=start_time,
                    completed_at=end_time,
                )
                await self._execution_repo.save_result(result)
                await self._event_repo.update_status(msg.work_item_id, EventStatus.COMPLETED)

                if self._idempotency_repo:
                    await self._idempotency_repo.mark_completed(idempotency_key, checkpoint.execution_id, output)

                # 8. ACK ONLY AFTER SUCCESSFUL DURABLE RESULT PERSISTENCE!
                if msg.transport_id:
                    await self._broker.acknowledge(msg.transport_id)

                self._tasks_completed += 1
                logger.info("Worker [%s] COMPLETED task '%s' (exec_id=%s)", self.worker_id, msg.work_item_id, checkpoint.execution_id)
                self._current_task = None
                return True

            except Exception as err:
                end_time = datetime.now(timezone.utc)
                err_category = type(err).__name__
                logger.warning("Worker [%s] task '%s' failed attempt %d: %s", self.worker_id, msg.work_item_id, attempt, err)

                if self._retry_policy.should_retry(err, attempt):
                    logger.info("Worker [%s] scheduling retry for task '%s' (attempt %d)", self.worker_id, msg.work_item_id, attempt + 1)
                    self._current_task = None
                    return False
                else:
                    # Max attempts reached or non-retryable error
                    result = ExecutionResult(
                        execution_id=checkpoint.execution_id,
                        work_item_id=msg.work_item_id,
                        status="FAILED",
                        output_data={"error": str(err)},
                        error_category=err_category,
                        attempt_number=attempt,
                        started_at=start_time,
                        completed_at=end_time,
                    )
                    await self._execution_repo.save_result(result)
                    await self._event_repo.update_status(msg.work_item_id, EventStatus.FAILED)
                    if self._idempotency_repo:
                        await self._idempotency_repo.mark_failed(idempotency_key, checkpoint.execution_id, str(err))

                    self._tasks_failed += 1
                    self._current_task = None
                    return False

    async def run_once(self) -> int:
        """Run single consumer poll loop iteration. Returns count of processed messages."""
        messages = await self._broker.consume(consumer_name=self.worker_id, count=1)
        if not messages:
            return 0

        for msg in messages:
            await self.process_message(msg)
        return len(messages)
