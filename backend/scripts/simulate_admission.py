"""CLI Script for 10x Overload Admission Control Simulation.

Simulates 1,000 incoming work items against a constrained capacity pool (100 units),
demonstrating value-aware capacity allocation, tenant quota guardrails, and starvation aging.

Usage:
    python -m scripts.simulate_admission
    python scripts/simulate_admission.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.models import (
    SignalEvent,
    CapacityState,
    TenantState,
)
from app.domain.enums import SeverityLevel, AdmissionDecision as AdmissionDecisionEnum
from app.valuation.service import ValueEstimationService
from app.valuation.rule_estimator import RuleBasedValueEstimator
from app.admission.controller import AdmissionController


async def run_admission_simulation(count: int = 1000) -> None:
    """Run admission control simulation with 1,000 work items under overload."""
    print(f"Starting Ledger Phase 4 Admission Simulation ({count} work items)...")

    valuation_service = ValueEstimationService(
        estimator=RuleBasedValueEstimator(),
        mode="rule_based",
    )
    admission_controller = AdmissionController()

    now = datetime.now(timezone.utc)

    # Global capacity constraint: 100 compute units total
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)

    # Multi-tenant state setup
    tenants = {
        "tenant_alpha": TenantState(tenant_id="tenant_alpha", quota=60.0),
        "tenant_beta": TenantState(tenant_id="tenant_beta", quota=30.0),
    }

    admitted_count = 0
    deferred_count = 0
    shed_count = 0
    consumed_compute = 0.0

    print("Processing incoming burst workload...")

    for i in range(count):
        # Determine severity distribution: 10% critical, 20% high, 40% medium, 30% info/low
        if i % 10 == 0:
            sev = SeverityLevel.CRITICAL
            evt_type = "payment_gateway_timeout"
            t_id = "tenant_alpha"
        elif i % 5 == 0:
            sev = SeverityLevel.HIGH
            evt_type = "database_connection_spike"
            t_id = "tenant_beta"
        elif i % 2 == 0:
            sev = SeverityLevel.MEDIUM
            evt_type = "api_latency_warning"
            t_id = "tenant_alpha"
        else:
            sev = SeverityLevel.INFO
            evt_type = "routine_log_sync"
            t_id = "tenant_alpha"

        event = SignalEvent(
            source_type="github" if i % 2 == 0 else "incident",
            source_id=f"sim_src_{i}",
            tenant_id=t_id,
            payload_hash=f"{i:064x}",
            coalesce_key=f"sim_key_{i % 10}",
            event_type=evt_type,
            severity=sev,
            raw_payload={"sim_index": i},
            created_at=now,
        )

        assessment = await valuation_service.assess_work_item(event)
        tenant_state = tenants[t_id]

        decision = admission_controller.evaluate_admission(
            work_item=event,
            assessment=assessment,
            capacity=capacity,
            tenant=tenant_state,
            evaluation_time=now,
        )

        if decision.decision == AdmissionDecisionEnum.ADMIT:
            admitted_count += 1
            capacity.available_capacity -= decision.capacity_required
            capacity.active_compute += decision.capacity_required
            tenant_state.current_usage += decision.capacity_required
            consumed_compute += decision.capacity_required
        elif decision.decision == AdmissionDecisionEnum.DEFER:
            deferred_count += 1
        else:
            shed_count += 1

    print("\n" + "=" * 65)
    print(" LEDGER ADMISSION CONTROL SIMULATION SUMMARY ")
    print("=" * 65)
    print(f"Total Incoming Work Items:    {count}")
    print(f"Total Compute Capacity Pool:  100.00 units")
    print(f"Total Admitted Work Items:    {admitted_count} (Consumed: {consumed_compute:.2f} units)")
    print(f"Total Deferred Work Items:    {deferred_count}")
    print(f"Total Shed Work Items:        {shed_count}")
    print(f"Remaining Available Capacity: {capacity.available_capacity:.2f} units")
    print("=" * 65)

    # Demonstrate Aging / Starvation Prevention
    print("\nDemonstrating Aging & Starvation Prevention...")
    old_medium_event = SignalEvent(
        source_type="github",
        source_id="aged_999",
        tenant_id="tenant_beta",
        payload_hash="f" * 64,
        coalesce_key="k_aged",
        event_type="routine_task",
        severity=SeverityLevel.MEDIUM,
        raw_payload={"task": "aged"},
        created_at=now - timedelta(minutes=15),  # Waiting 15 minutes!
    )
    aged_assessment = await valuation_service.assess_work_item(old_medium_event)
    aged_capacity = CapacityState(total_capacity=100.0, available_capacity=10.0)
    aged_tenant = TenantState(tenant_id="tenant_beta", quota=30.0, current_usage=0.0)

    aged_decision = admission_controller.evaluate_admission(
        work_item=old_medium_event,
        assessment=aged_assessment,
        capacity=aged_capacity,
        tenant=aged_tenant,
        evaluation_time=now,
    )
    print(f"Original Expected Value: {aged_assessment.expected_value}")
    print(f"Effective Value (Aged): {aged_decision.effective_value}")
    print(f"Decision Outcome:       {aged_decision.decision.value}")
    print(f"Explanation:            {aged_decision.explanation}")
    print("=" * 65)


def main() -> None:
    asyncio.run(run_admission_simulation(count=1000))


if __name__ == "__main__":
    main()
