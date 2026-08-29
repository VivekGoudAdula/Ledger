"""Unit Tests for RuleBasedValueEstimator.

Validates severity mapping, keyword consequence scoring, and coalesced incident scaling.
"""

import pytest
from app.domain.models import SignalEvent, CoalescedIncident
from app.domain.enums import SeverityLevel
from app.valuation.rule_estimator import RuleBasedValueEstimator


@pytest.mark.asyncio
async def test_rule_based_estimator_severity_mapping():
    estimator = RuleBasedValueEstimator()

    critical_event = SignalEvent(
        source_type="github",
        source_id="c1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        event_type="test",
        severity=SeverityLevel.CRITICAL,
        raw_payload={"test": "payload"},
    )

    info_event = SignalEvent(
        source_type="github",
        source_id="i1",
        tenant_id="t1",
        payload_hash="b" * 64,
        coalesce_key="k2",
        event_type="test",
        severity=SeverityLevel.INFO,
        raw_payload={"test": "payload"},
    )

    assessment_crit = await estimator.estimate(critical_event)
    assessment_info = await estimator.estimate(info_event)

    assert assessment_crit.urgency > assessment_info.urgency
    assert assessment_crit.urgency == 0.90
    assert assessment_info.urgency == 0.15


@pytest.mark.asyncio
async def test_rule_based_estimator_keyword_consequence():
    estimator = RuleBasedValueEstimator()

    payment_event = SignalEvent(
        source_type="github",
        source_id="p1",
        tenant_id="t1",
        payload_hash="a" * 64,
        coalesce_key="k1",
        event_type="payment_gateway_timeout",
        severity=SeverityLevel.HIGH,
        raw_payload={"test": "payload"},
    )

    assessment = await estimator.estimate(payment_event)
    assert assessment.consequence_of_drop == 0.90


@pytest.mark.asyncio
async def test_rule_based_estimator_coalesced_incident_scaling():
    estimator = RuleBasedValueEstimator()

    incident = CoalescedIncident(
        tenant_id="t1",
        coalesce_key="k_inc",
        representative_title="Payment Gateway Outage Spike",
        source_types=["github"],
        event_ids=["e1", "e2"],
        signal_count=20,
        coalescing_method="deterministic_fingerprint",
    )

    assessment = await estimator.estimate(incident)
    assert assessment.work_item_type == "incident"
    assert assessment.urgency >= 0.80
    assert assessment.consequence_of_drop >= 0.85
