"""Unit Tests for Benchmark Admission Policies.

Validates FIFO baseline arrival order capacity enforcement and Ledger Phase 4 policy evaluation.
"""

from datetime import datetime, timezone

from app.domain.models import CapacityState, TenantState
from app.domain.enums import DecisionType
from app.benchmark.models import BenchmarkConfig
from app.benchmark.workload import WorkloadGenerator
from app.benchmark.policies import FIFOPolicy, LedgerPolicyAdapter


def test_fifo_policy_capacity_admission():
    policy = FIFOPolicy()
    gen = WorkloadGenerator(seed=42)
    config = BenchmarkConfig(scenario="normal_load", seed=42)
    workload = gen.generate_workload(config)

    now = datetime.now(timezone.utc)
    capacity = CapacityState(total_capacity=10.0, available_capacity=10.0)
    tenant = TenantState(tenant_id="tenant_bench", quota=10.0)

    # First item under capacity -> ADMIT
    decision1 = policy.evaluate(workload[0], capacity, tenant, now)
    assert decision1.decision == DecisionType.ADMIT

    # Zero capacity -> DEFER
    zero_cap = CapacityState(total_capacity=10.0, available_capacity=0.0)
    decision2 = policy.evaluate(workload[0], zero_cap, tenant, now)
    assert decision2.decision == DecisionType.DEFER


def test_ledger_policy_adapter_evaluation():
    adapter = LedgerPolicyAdapter()
    gen = WorkloadGenerator(seed=42)
    config = BenchmarkConfig(scenario="normal_load", seed=42)
    workload = gen.generate_workload(config)

    now = datetime.now(timezone.utc)
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id="tenant_bench", quota=50.0)

    decision = adapter.evaluate(workload[0], capacity, tenant, now)
    assert decision.decision in (DecisionType.ADMIT, DecisionType.DEFER, DecisionType.SHED)
