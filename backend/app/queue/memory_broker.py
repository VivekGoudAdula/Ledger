"""In-Memory Work Queue Broker Adapter.

Provides zero-dependency, in-memory implementation of WorkQueueInterface for testing and offline fallback.
"""

from datetime import datetime, timezone
from typing import Any

from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum
from app.domain.models import (
    SignalEvent,
    CoalescedIncident,
    AdmissionDecision,
    QueueMessage,
    QueueMetrics,
)
from app.domain.interfaces.queue import WorkQueueInterface


class InMemoryWorkQueue(WorkQueueInterface):
    """In-memory implementation of WorkQueueInterface with consumer group simulation."""

    def __init__(self, stream_name: str = "ledger:memory_stream", group_name: str = "memory_workers") -> None:
        self.stream_name = stream_name
        self.group_name = group_name
        self._messages: list[QueueMessage] = []
        self._pending: dict[str, QueueMessage] = {}  # transport_id -> QueueMessage
        self._pending_times: dict[str, datetime] = {}  # transport_id -> last_delivered_at
        self._acknowledged: set[str] = set()
        self._consumers: set[str] = set()
        self._counter = 0

    async def publish(
        self, work_item: SignalEvent | CoalescedIncident, decision: AdmissionDecision
    ) -> QueueMessage:
        """Publish an admitted work item to the in-memory stream."""
        if decision.decision != AdmissionDecisionEnum.ADMIT:
            raise ValueError(f"Cannot enqueue decision '{decision.decision.value}'. Only ADMIT decisions are queueable.")

        work_id = work_item.event_id if isinstance(work_item, SignalEvent) else work_item.incident_id
        self._counter += 1
        transport_id = f"mem-{self._counter:06d}-0"

        msg = QueueMessage(
            work_item_id=work_id,
            tenant_id=work_item.tenant_id,
            effective_value=decision.effective_value,
            value_per_compute=decision.value_per_compute,
            admission_decision_id=decision.decision_id,
            transport_id=transport_id,
        )

        self._messages.append(msg)
        return msg

    async def consume(
        self, consumer_name: str, count: int = 1
    ) -> list[QueueMessage]:
        """Consume messages assigned to a consumer within the group."""
        self._consumers.add(consumer_name)
        now = datetime.now(timezone.utc)
        consumed = []
        for msg in self._messages:
            if msg.transport_id not in self._pending and msg.transport_id not in self._acknowledged:
                self._pending[msg.transport_id] = msg
                self._pending_times[msg.transport_id] = now
                consumed.append(msg)
                if len(consumed) >= count:
                    break
        return consumed

    async def claim_stale_messages(
        self, consumer_name: str, min_idle_ms: int, count: int = 10
    ) -> list[QueueMessage]:
        """Reclaim unacknowledged messages idle longer than min_idle_ms."""
        self._consumers.add(consumer_name)
        now = datetime.now(timezone.utc)
        reclaimed = []

        for t_id, msg in list(self._pending.items()):
            if t_id in self._acknowledged:
                continue
            last_delivered = self._pending_times.get(t_id, msg.enqueued_at)
            idle_ms = (now - last_delivered).total_seconds() * 1000.0
            if idle_ms >= min_idle_ms:
                self._pending_times[t_id] = now  # Reset idle timer upon reclaim
                reclaimed.append(msg)
                if len(reclaimed) >= count:
                    break
        return reclaimed

    async def acknowledge(self, transport_id: str) -> bool:
        """Acknowledge successful message processing."""
        if transport_id in self._pending:
            del self._pending[transport_id]
            self._pending_times.pop(transport_id, None)
            self._acknowledged.add(transport_id)
            return True
        return False

    async def get_pending_messages(self) -> list[dict[str, Any]]:
        """Retrieve unacknowledged pending messages."""
        return [
            {
                "transport_id": t_id,
                "work_item_id": msg.work_item_id,
                "tenant_id": msg.tenant_id,
                "enqueued_at": msg.enqueued_at.isoformat(),
            }
            for t_id, msg in self._pending.items()
        ]

    async def get_metrics(self) -> QueueMetrics:
        """Retrieve queue metrics."""
        return QueueMetrics(
            stream_length=len(self._messages) - len(self._acknowledged),
            pending_count=len(self._pending),
            consumer_count=len(self._consumers),
            stream_name=self.stream_name,
            consumer_group=self.group_name,
        )

    async def check_health(self) -> dict[str, Any]:
        """Check broker health status."""
        return {
            "broker": "memory",
            "status": "healthy",
            "stream": self.stream_name,
            "consumer_group": self.group_name,
        }
