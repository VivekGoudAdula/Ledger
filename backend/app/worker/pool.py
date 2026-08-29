"""Worker Pool Supervisor.

Manages multi-worker topology, failure isolation, and graceful shutdown orchestration.
"""

import asyncio
import logging
from typing import Sequence

from app.domain.models import WorkerStatus
from app.worker.worker import LedgerWorker

logger = logging.getLogger(__name__)


class WorkerPool:
    """Supervisor for managing multiple worker instances concurrently."""

    def __init__(self, workers: Sequence[LedgerWorker]) -> None:
        self._workers = list(workers)
        self._running = False
        self._tasks: list[asyncio.Task] = []

    @property
    def workers(self) -> list[LedgerWorker]:
        """Return worker instances."""
        return self._workers

    def get_pool_status(self) -> list[WorkerStatus]:
        """Retrieve telemetry status for all managed workers."""
        return [w.get_status() for w in self._workers]

    async def run_step(self) -> int:
        """Run single step across all workers in parallel with failure isolation."""
        async def _safe_step(w: LedgerWorker) -> int:
            try:
                return await w.run_once()
            except Exception as err:
                logger.error("Worker [%s] encountered loop error: %s", w.worker_id, err)
                return 0

        results = await asyncio.gather(*[_safe_step(w) for w in self._workers])
        return sum(results)

    async def start(self, poll_interval_seconds: float = 0.1) -> None:
        """Start worker pool background polling loop."""
        self._running = True
        logger.info("WorkerPool starting with %d workers...", len(self._workers))
        while self._running:
            await self.run_step()
            await asyncio.sleep(poll_interval_seconds)

    async def stop(self) -> None:
        """Gracefully stop worker pool."""
        logger.info("WorkerPool shutting down...")
        self._running = False
        for t in self._tasks:
            t.cancel()
        logger.info("WorkerPool shutdown complete.")
