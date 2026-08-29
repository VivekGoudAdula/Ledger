"""Unit Tests for Idempotency Domain Entities.

Validates key generation helper, format contracts, and field boundaries.
"""

import pytest

from app.domain.enums import IdempotencyStatus, ActionType
from app.domain.models import IdempotencyRecord, generate_idempotency_key


def test_generate_idempotency_key_valid():
    key1 = generate_idempotency_key("tenant_a", "item_123", "ANALYZE_SIGNAL")
    assert key1 == "tenant_a:item_123:ANALYZE_SIGNAL"

    key2 = generate_idempotency_key("tenant_b", "item_456", ActionType.AGGREGATE_INCIDENT)
    assert key2 == "tenant_b:item_456:AGGREGATE_INCIDENT"


@pytest.mark.parametrize("invalid_tenant", ["", None, 123])
def test_generate_key_invalid_tenant_rejected(invalid_tenant):
    with pytest.raises(ValueError, match="tenant_id"):
        generate_idempotency_key(invalid_tenant, "item_123", "ANALYZE_SIGNAL")


def test_valid_idempotency_record_construction():
    rec = IdempotencyRecord(
        tenant_id="tenant_x",
        work_item_id="item_789",
        action_type="PROCESS_ALERT",
    )
    assert rec.idempotency_key == "tenant_x:item_789:PROCESS_ALERT"
    assert rec.status == IdempotencyStatus.IN_PROGRESS
