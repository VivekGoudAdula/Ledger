"""Work Queue Interface Protocol.

Provides a broker-agnostic abstraction for publishing, consuming, acknowledging, and reclaiming stale work.
"""

from typing import Protocol, runtime_checkable, Any
from app.domain.models import (
    SignalEvent,
    CoalescedIncident,
    AdmissionDecision,
    QueueMessage,
    QueueMetrics,
)


@runtime_checkable
class WorkQueueInterface(Protocol):
    """Protocol interface for work transport queue brokers (Redis, Memory, Kafka)."""

    async def publish(
        self, work_item: SignalEvent | CoalescedIncident, decision: AdmissionDecision
    ) -> QueueMessage:
        """Publish an admitted work item to the transport queue."""
        ...

    async def consume(
        self, consumer_name: str, count: int = 1
    ) -> list[QueueMessage]:
        """Consume messages assigned to a consumer within the consumer group."""
        ...

    async def acknowledge(self, transport_id: str) -> bool:
        """Acknowledge successful message processing (removes message from pending list)."""
        ...

    async def claim_stale_messages(
        self, consumer_name: str, min_idle_ms: int, count: int = 10
    ) -> list[QueueMessage]:
        """Reclaim unacknowledged messages idle longer than min_idle_ms."""
        ...

    async def get_pending_messages(self) -> list[dict[str, Any]]:
        """Retrieve unacknowledged pending entries for observability."""
        ...

    async def get_metrics(self) -> QueueMetrics:
        """Retrieve queue depth, pending counts, and consumer metrics."""
        ...

    async def check_health(self) -> dict[str, Any]:
        """Check broker connectivity and stream health status."""
        ...
