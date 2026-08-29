"""CLI Script for Signal Valuation Demonstration.

Demonstrates ValueAssessment generation across diverse signal profiles (critical payment alerts,
minor warnings, expired deadlines, coalesced incidents, and AI fallback).

Usage:
    python -m scripts.test_valuation
    python scripts/test_valuation.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.database import init_db, AsyncSessionLocal
from app.storage.repositories import EventRepository, IncidentRepository, ValuationRepository
from app.domain.models import SignalEvent, CoalescedIncident
from app.domain.enums import SeverityLevel
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.valuation.ai_estimator import LLMValueEstimator


async def run_valuation_demo() -> None:
    """Run valuation demonstration across diverse work items."""
    await init_db()

    print("Initializing Ledger Value Estimation Service...")

    async with AsyncSessionLocal() as session:
        valuation_repo = ValuationRepository(session)
        rule_estimator = RuleBasedValueEstimator()
        
        # Test with Rule-Based Service first
        service = ValueEstimationService(
            estimator=rule_estimator,
            repository=valuation_repo,
            mode="rule_based",
        )

        now = datetime.now(timezone.utc)

        # Profile 1: Critical Payment Failure
        payment_event = SignalEvent(
            source_type="github",
            source_id="pay_999",
            tenant_id="demo_tenant",
            payload_hash="1" * 64,
            coalesce_key="key_pay",
            event_type="payment_gateway_outage_alert",
            severity=SeverityLevel.CRITICAL,
            raw_payload={"alert": "Payment Gateway Timeout Spike", "affected_service": "checkout-api"},
            created_at=now,
        )

        # Profile 2: Minor Background Log Info
        info_event = SignalEvent(
            source_type="github",
            source_id="info_111",
            tenant_id="demo_tenant",
            payload_hash="2" * 64,
            coalesce_key="key_info",
            event_type="routine_log_rotation",
            severity=SeverityLevel.INFO,
            raw_payload={"log": "routine maintenance cycle complete"},
            created_at=now,
        )

        # Profile 3: Expired Deadline Signal
        expired_event = SignalEvent(
            source_type="incident",
            source_id="exp_222",
            tenant_id="demo_tenant",
            payload_hash="3" * 64,
            coalesce_key="key_exp",
            event_type="temporary_cache_warmup",
            severity=SeverityLevel.HIGH,
            deadline_at=now - timedelta(minutes=10),  # Expired 10m ago!
            raw_payload={"task": "warmup"},
            created_at=now - timedelta(minutes=30),
        )

        # Profile 4: Large Coalesced Incident
        incident = CoalescedIncident(
            tenant_id="demo_tenant",
            coalesce_key="incident_pay_spike",
            representative_title="[GITHUB] Payment Failure Spike Across Services",
            source_types=["github", "datadog"],
            event_ids=["e1", "e2", "e3"],
            signal_count=50,
            coalescing_method="deterministic_fingerprint",
            first_seen=now - timedelta(minutes=5),
            last_seen=now,
        )

        work_items = [
            ("Critical Payment Outage", payment_event),
            ("Routine Maintenance Info", info_event),
            ("Expired Deadline Task", expired_event),
            ("50x Coalesced Incident", incident),
        ]

        print("\n" + "=" * 95)
        print(f"{'WORK ITEM PROFILE':<25} | {'URGENCY':<7} | {'CONF':<5} | {'DROP COST':<9} | {'COMPUTE':<7} | {'EV':<6} | {'V/COMP':<6} | {'ESTIMATOR'}")
        print("=" * 95)

        for name, item in work_items:
            assessment = await service.assess_work_item(item)
            print(
                f"{name:<25} | "
                f"{assessment.urgency:<7.2f} | "
                f"{assessment.confidence:<5.2f} | "
                f"{assessment.consequence_of_drop:<9.2f} | "
                f"{assessment.estimated_compute_cost:<7.2f} | "
                f"{assessment.expected_value:<6.4f} | "
                f"{assessment.value_per_compute:<6.4f} | "
                f"{assessment.estimator}"
            )
        print("=" * 95)

        # Profile 5: AI Estimator Fallback Test
        print("\nDemonstrating AI Estimator Failure -> Rule-Based Fallback Protection...")
        unconfigured_ai_estimator = LLMValueEstimator()  # No HTTP client -> will fail & trigger fallback!
        fallback_service = ValueEstimationService(
            estimator=unconfigured_ai_estimator,
            repository=valuation_repo,
            mode="llm_with_fallback",
        )

        fb_assessment = await fallback_service.assess_work_item(payment_event)
        print(f"Fallback Triggered:   {fb_assessment.is_fallback}")
        print(f"Assigned Estimator:   {fb_assessment.estimator}")
        print(f"Expected Value:       {fb_assessment.expected_value}")
        print(f"Explainable Rationale: {fb_assessment.rationale}")
        print("=" * 95)

        await session.commit()


def main() -> None:
    asyncio.run(run_valuation_demo())


if __name__ == "__main__":
    main()
