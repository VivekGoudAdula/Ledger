"""Unit Tests for Ledger Telemetry Adapter.

Validates threshold evaluation, cooldown window enforcement, and feedback loop protection.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.domain.models import QueueMetrics
from app.domain.enums import SeverityLevel
from app.ingestion.sources import LedgerTelemetryAdapter


def test_telemetry_adapter_threshold_and_cooldown():
    adapter = LedgerTelemetryAdapter(cooldown_seconds=300.0)

    # 1. Normal metrics below threshold (pending=10) -> Should return None
    normal_metrics = QueueMetrics(
        pending_count=10,
        stream_length=10,
        consumer_count=2,
        stream_name="ledger:test_stream",
        consumer_group="test_group",
    )
    assert adapter.evaluate_metrics(normal_metrics) is None

    # 2. Anomalous metrics above threshold (pending=60) -> Should return SignalEvent
    anomalous_metrics = QueueMetrics(
        pending_count=60,
        stream_length=60,
        consumer_count=2,
        stream_name="ledger:test_stream",
        consumer_group="test_group",
    )
    evt1 = adapter.evaluate_metrics(anomalous_metrics, tenant_id="tenant_sys_test")
    assert evt1 is not None
    assert evt1.source_type == "telemetry"
    assert evt1.severity == SeverityLevel.HIGH
    assert evt1.raw_payload["observed_value"] == 60

    # 3. Repeated anomalous metrics within cooldown (300s) -> Should return None (cooldown active!)
    evt2 = adapter.evaluate_metrics(anomalous_metrics, tenant_id="tenant_sys_test")
    assert evt2 is None
