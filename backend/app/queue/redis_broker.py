"""Redis Streams Work Queue Broker Adapter.

Provides production Redis Streams infrastructure adapter for WorkQueueInterface.
Manages stream creation, consumer groups (XREADGROUP), pending entries (XPENDING), reclamation (XAUTOCLAIM), and ACKs (XACK).
"""

import logging
from typing import Any
import redis.asyncio as aioredis
from redis.exceptions import ResponseError, ConnectionError as RedisConnectionError

from app.config import settings
from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum
from app.domain.models import (
    SignalEvent,
    CoalescedIncident,
    AdmissionDecision,
    QueueMessage,
    QueueMetrics,
)
from app.domain.interfaces.queue import WorkQueueInterface

logger = logging.getLogger(__name__)


class RedisStreamBroker(WorkQueueInterface):
    """Production Redis Streams implementation of WorkQueueInterface."""

    def __init__(
        self,
        redis_client: aioredis.Redis | None = None,
        redis_url: str | None = None,
        stream_name: str | None = None,
        group_name: str | None = None,
    ) -> None:
        self.stream_name = stream_name or settings.LEDGER_STREAM_NAME
        self.group_name = group_name or settings.LEDGER_CONSUMER_GROUP
        self._url = redis_url or settings.REDIS_URL
        self._redis = redis_client or aioredis.from_url(self._url, decode_responses=True)
        self._initialized = False

    async def _ensure_stream_and_group(self) -> None:
        """Idempotently create stream and consumer group if not existing."""
        if self._initialized:
            return
        try:
            await self._redis.xgroup_create(
                name=self.stream_name,
                groupname=self.group_name,
                id="0",
                mkstream=True,
            )
        except ResponseError as err:
            if "BUSYGROUP" not in str(err):
                raise
        self._initialized = True

    async def publish(
        self, work_item: SignalEvent | CoalescedIncident, decision: AdmissionDecision
    ) -> QueueMessage:
        """Publish an admitted work item to Redis Stream (XADD)."""
        if decision.decision != AdmissionDecisionEnum.ADMIT:
            raise ValueError(f"Cannot enqueue decision '{decision.decision.value}'. Only ADMIT decisions are queueable.")

        await self._ensure_stream_and_group()
        work_id = work_item.event_id if isinstance(work_item, SignalEvent) else work_item.incident_id

        msg = QueueMessage(
            work_item_id=work_id,
            tenant_id=work_item.tenant_id,
            effective_value=decision.effective_value,
            value_per_compute=decision.value_per_compute,
            admission_decision_id=decision.decision_id,
        )

        transport_id = await self._redis.xadd(
            name=self.stream_name,
            fields=msg.to_dict(),
        )
        msg.transport_id = str(transport_id)
        return msg

    async def consume(
        self, consumer_name: str, count: int = 1
    ) -> list[QueueMessage]:
        """Consume new unassigned stream messages (XREADGROUP)."""
        await self._ensure_stream_and_group()
        raw_res = await self._redis.xreadgroup(
            groupname=self.group_name,
            consumername=consumer_name,
            streams={self.stream_name: ">"},
            count=count,
        )

        messages = []
        if not raw_res:
            return messages

        for _, stream_messages in raw_res:
            for t_id, data in stream_messages:
                msg = QueueMessage.from_dict(data, transport_id=str(t_id))
                messages.append(msg)

        return messages

    async def claim_stale_messages(
        self, consumer_name: str, min_idle_ms: int, count: int = 10
    ) -> list[QueueMessage]:
        """Reclaim unacknowledged messages idle longer than min_idle_ms via XAUTOCLAIM."""
        await self._ensure_stream_and_group()
        try:
            res = await self._redis.xautoclaim(
                name=self.stream_name,
                groupname=self.group_name,
                consumername=consumer_name,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=count,
            )
            claimed_msgs = []
            if res and len(res) >= 2:
                for t_id, data in res[1]:
                    if data:
                        claimed_msgs.append(QueueMessage.from_dict(data, transport_id=str(t_id)))
            return claimed_msgs
        except ResponseError as err:
            logger.warning("XAUTOCLAIM failed or unssupported, falling back: %s", err)
            return []

    async def acknowledge(self, transport_id: str) -> bool:
        """Acknowledge message execution completion (XACK)."""
        await self._ensure_stream_and_group()
        ack_count = await self._redis.xack(self.stream_name, self.group_name, transport_id)
        return ack_count > 0

    async def get_pending_messages(self) -> list[dict[str, Any]]:
        """Retrieve pending unacknowledged message entries (XPENDING_RANGE)."""
        await self._ensure_stream_and_group()
        pending = await self._redis.xpending_range(
            name=self.stream_name,
            groupname=self.group_name,
            min="-",
            max="+",
            count=100,
        )
        return [
            {
                "transport_id": item["message_id"],
                "consumer": item["consumer"],
                "idle_ms": item["idle"],
                "deliveries": item["delivery_count"],
            }
            for item in pending
        ]

    async def get_metrics(self) -> QueueMetrics:
        """Retrieve queue metrics (XLEN and XPENDING)."""
        await self._ensure_stream_and_group()
        length = await self._redis.xlen(self.stream_name)
        pending_info = await self._redis.xpending(self.stream_name, self.group_name)

        return QueueMetrics(
            stream_length=length,
            pending_count=pending_info.get("pending", 0) if isinstance(pending_info, dict) else 0,
            consumer_count=len(pending_info.get("consumers", [])) if isinstance(pending_info, dict) else 0,
            stream_name=self.stream_name,
            consumer_group=self.group_name,
        )

    async def check_health(self) -> dict[str, Any]:
        """Check Redis broker connectivity and health."""
        try:
            pong = await self._redis.ping()
            return {
                "broker": "redis",
                "status": "healthy" if pong else "unhealthy",
                "stream": self.stream_name,
                "consumer_group": self.group_name,
            }
        except RedisConnectionError as err:
            return {
                "broker": "redis",
                "status": "unhealthy",
                "error": str(err),
            }
