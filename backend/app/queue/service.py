"""Queue Publisher Application Service.

Orchestrates transport routing of AdmissionDecisions into the WorkQueueInterface broker.
Enforces ADMIT-only publishing while preserving DEFERRED and SHED state tracking.
"""

import logging
from typing import Tuple

from app.domain.enums import EventStatus, AdmissionDecision as AdmissionDecisionEnum
from app.domain.models import (
    SignalEvent,
    CoalescedIncident,
    AdmissionDecision,
    QueueMessage,
)
from app.domain.interfaces.queue import WorkQueueInterface
from app.domain.interfaces.repositories import EventRepositoryInterface
from app.queue.memory_broker import InMemoryWorkQueue

logger = logging.getLogger(__name__)


class QueuePublisherService:
    """Service managing work item queue publication based on admission decisions."""

    def __init__(
        self,
        broker: WorkQueueInterface | None = None,
        event_repo: EventRepositoryInterface | None = None,
    ) -> None:
        self._broker = broker or InMemoryWorkQueue()
        self._event_repo = event_repo

    async def handle_admission_decision(
        self,
        work_item: SignalEvent | CoalescedIncident,
        decision: AdmissionDecision,
    ) -> tuple[EventStatus, QueueMessage | None]:
        """Route work item based on admission decision outcome.

        Returns:
            Tuple of (final_event_status, QueueMessage_if_enqueued)
        """
        work_id = work_item.event_id if isinstance(work_item, SignalEvent) else work_item.incident_id

        if decision.decision == AdmissionDecisionEnum.ADMIT:
            # Publish to active transport broker stream
            msg = await self._broker.publish(work_item, decision)
            status = EventStatus.QUEUED
            if isinstance(work_item, SignalEvent):
                work_item.mark_status(status)
            if self._event_repo and isinstance(work_item, SignalEvent):
                await self._event_repo.update_status(work_id, status)

            logger.info("Enqueued ADMITTED work item '%s' to transport (msg_id=%s)", work_id, msg.message_id)
            return status, msg

        elif decision.decision == AdmissionDecisionEnum.DEFER:
            status = EventStatus.DEFERRED
            if isinstance(work_item, SignalEvent):
                work_item.mark_status(status)
            if self._event_repo and isinstance(work_item, SignalEvent):
                await self._event_repo.update_status(work_id, status)

            logger.info("DEFERRED work item '%s' (defer_until=%s)", work_id, decision.defer_until)
            return status, None

        else:
            status = EventStatus.SHED
            if isinstance(work_item, SignalEvent):
                work_item.mark_status(status)
            if self._event_repo and isinstance(work_item, SignalEvent):
                await self._event_repo.update_status(work_id, status)

            logger.info("SHED work item '%s' (reason=%s)", work_id, decision.reason.value)
            return status, None
