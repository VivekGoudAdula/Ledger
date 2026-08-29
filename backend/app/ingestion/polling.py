"""Source Polling Service.

Orchestrates periodic polling of GitHub, Public Status Feed, and Telemetry sources independently,
normalizes items into canonical SignalEvent entities, and submits them to IngestionService.
"""

import logging
from typing import Any

from app.ingestion.service import IngestionService
from app.ingestion.sources import (
    GitHubClient,
    GitHubSourceAdapter,
    GitHubAPIException,
    StatusFeedClient,
    StatusFeedAdapter,
    StatusFeedException,
    LedgerTelemetryAdapter,
)
from app.domain.interfaces.queue import WorkQueueInterface
from app.domain.models import SignalEvent

logger = logging.getLogger(__name__)


class SourcePollingService:
    """Orchestrates multi-source polling with source isolation and ingestion integration."""

    def __init__(
        self,
        ingestion_service: IngestionService,
        broker: WorkQueueInterface | None = None,
        github_client: GitHubClient | None = None,
        status_client: StatusFeedClient | None = None,
    ) -> None:
        self._ingestion = ingestion_service
        self._broker = broker
        self._gh_client = github_client or GitHubClient()
        self._gh_adapter = GitHubSourceAdapter()
        self._status_client = status_client or StatusFeedClient()
        self._status_adapter = StatusFeedAdapter()
        self._telemetry_adapter = LedgerTelemetryAdapter()

    async def poll_github(self, tenant_id: str = "tenant_github", limit: int = 10) -> list[SignalEvent]:
        """Poll public GitHub events with rate-limit protection."""
        events = []
        try:
            raw_items = await self._gh_client.fetch_public_events(limit=limit)
            for raw in raw_items:
                try:
                    evt = self._gh_adapter.parse_raw({}, raw, tenant_id)
                    saved_evt, _ = await self._ingestion.ingest_event(evt)
                    if saved_evt:
                        events.append(saved_evt)
                except Exception as err:
                    logger.warning("Failed to parse/ingest GitHub event: %s", err)
        except GitHubAPIException as err:
            logger.warning("GitHub poller encountered API error: %s", err)
        return events

    async def poll_status_feed(self, tenant_id: str = "tenant_status") -> list[SignalEvent]:
        """Poll public status page incidents."""
        events = []
        try:
            raw_incidents = await self._status_client.fetch_incidents()
            for raw in raw_incidents:
                try:
                    evt = self._status_adapter.parse_raw({}, raw, tenant_id)
                    saved_evt, _ = await self._ingestion.ingest_event(evt)
                    if saved_evt:
                        events.append(saved_evt)
                except Exception as err:
                    logger.warning("Failed to parse/ingest status feed incident: %s", err)
        except StatusFeedException as err:
            logger.warning("Status feed poller encountered API error: %s", err)
        return events

    async def poll_telemetry(self, tenant_id: str = "tenant_system") -> list[SignalEvent]:
        """Evaluate application runtime telemetry for operational anomalies."""
        events = []
        if not self._broker:
            return events
        try:
            metrics = await self._broker.get_metrics()
            evt = self._telemetry_adapter.evaluate_metrics(metrics, tenant_id)
            if evt:
                saved_evt, _ = await self._ingestion.ingest_event(evt)
                if saved_evt:
                    events.append(saved_evt)
        except Exception as err:
            logger.warning("Telemetry poller encountered error: %s", err)
        return events

    async def run_full_polling_cycle(
        self,
        gh_tenant: str = "tenant_github",
        status_tenant: str = "tenant_status",
        telemetry_tenant: str = "tenant_system",
    ) -> dict[str, Any]:
        """Execute isolated polling cycle across all sources."""
        gh_events = await self.poll_github(tenant_id=gh_tenant)
        status_events = await self.poll_status_feed(tenant_id=status_tenant)
        telem_events = await self.poll_telemetry(tenant_id=telemetry_tenant)

        return {
            "github_events_ingested": len(gh_events),
            "status_events_ingested": len(status_events),
            "telemetry_events_ingested": len(telem_events),
            "total_ingested": len(gh_events) + len(status_events) + len(telem_events),
        }
