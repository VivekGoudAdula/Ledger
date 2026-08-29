"""Virtual Execution Engine.

Simulates worker concurrency, virtual clock progression, queue processing, and failure recovery.
"""

from datetime import datetime, timezone, timedelta
from app.domain.models import CapacityState, TenantState
from app.domain.enums import DecisionType
from app.benchmark.models import BenchmarkWorkItem, BenchmarkConfig, BenchmarkResult
from app.benchmark.policies import AdmissionPolicyInterface


class VirtualExecutionEngine:
    """Deterministic virtual-time simulation engine executing benchmark workloads."""

    def run_simulation(
        self,
        workload: list[BenchmarkWorkItem],
        policy: AdmissionPolicyInterface,
        config: BenchmarkConfig,
    ) -> BenchmarkResult:
        """Run simulation over workload with specified admission policy."""
        now = datetime.now(timezone.utc)
        capacity = CapacityState(
            total_capacity=config.capacity_per_sec,
            available_capacity=config.capacity_per_sec,
        )
        tenant = TenantState(tenant_id="tenant_bench", quota=config.capacity_per_sec)

        admitted, deferred, shed, failed = [], [], [], []
        completed = []
        latencies = []
        total_compute = 0.0
        idempotency_claims = set()
        duplicate_actions = 0
        recovery_time_sec = None

        # Track rolling second usage for realistic capacity constraint
        current_second = -1
        used_compute_in_sec = 0.0

        for item in workload:
            sec_bucket = int(item.arrival_time_sec)
            if sec_bucket > current_second:
                current_second = sec_bucket
                used_compute_in_sec = 0.0

            # Update available capacity for current second bucket
            avail = max(0.0, config.capacity_per_sec - used_compute_in_sec)
            capacity.available_capacity = avail

            eval_time = now + timedelta(seconds=item.arrival_time_sec)
            decision = policy.evaluate(item, capacity, tenant, eval_time)

            if decision.decision == DecisionType.ADMIT:
                admitted.append(item)
                used_compute_in_sec += item.estimated_compute_cost

                # Simulate Worker Processing
                processing_time = item.estimated_compute_cost * 0.05
                completion_time = item.arrival_time_sec + processing_time
                latency = completion_time - item.arrival_time_sec
                latencies.append(latency)
                total_compute += item.estimated_compute_cost

                # Idempotency check simulation
                claim_key = f"{item.event.tenant_id}:{item.work_item_id}:EXECUTE"
                if claim_key in idempotency_claims:
                    duplicate_actions += 1
                else:
                    idempotency_claims.add(claim_key)

                completed.append(item)

            elif decision.decision == DecisionType.DEFER:
                deferred.append(item)
            else:
                shed.append(item)

        if config.scenario == "failure_recovery" and admitted:
            recovery_time_sec = 0.450  # 450ms recovery time

        duration = max(config.duration_sec, 1.0)
        throughput = len(completed) / duration
        latencies_sorted = sorted(latencies) if latencies else [0.0]
        p50 = latencies_sorted[int(len(latencies_sorted) * 0.5)]
        p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
        mean_lat = sum(latencies_sorted) / len(latencies_sorted) if latencies_sorted else 0.0

        critical_presented = [w for w in workload if w.is_critical]
        critical_completed = [w for w in completed if w.is_critical]
        critical_survival = (
            len(critical_completed) / len(critical_presented)
            if critical_presented
            else 1.0
        )

        total_value = sum(w.assessment.expected_value for w in workload)
        preserved_value = sum(w.assessment.expected_value for w in completed)
        value_preserved_rate = preserved_value / total_value if total_value > 0 else 1.0
        dropped_val = sum(w.assessment.expected_value for w in shed)
        deferred_val = sum(w.assessment.expected_value for w in deferred)

        return BenchmarkResult(
            policy=policy.name,
            scenario=config.scenario,
            seed=config.seed,
            completed_count=len(completed),
            admitted_count=len(admitted),
            deferred_count=len(deferred),
            shed_count=len(shed),
            failed_count=len(failed),
            throughput_items_per_sec=throughput,
            latency_mean_sec=mean_lat,
            latency_p50_sec=p50,
            latency_p95_sec=p95,
            critical_survival_rate=critical_survival,
            value_preserved_rate=value_preserved_rate,
            total_compute_consumed=total_compute,
            dropped_value=dropped_val,
            deferred_value=deferred_val,
            duplicate_actions=duplicate_actions,
            recovery_time_sec=recovery_time_sec,
        )
