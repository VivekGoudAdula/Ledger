"""Workload Generator.

Produces reproducible, seed-based BenchmarkWorkItem sequences across standardized operational scenarios.
"""

import random
from datetime import datetime, timezone, timedelta

from app.domain.models import SignalEvent, ValueAssessment
from app.domain.enums import SeverityLevel
from app.benchmark.models import BenchmarkWorkItem, BenchmarkConfig


class WorkloadGenerator:
    """Generates deterministic benchmark workloads given a seed and scenario config."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    def generate_workload(self, config: BenchmarkConfig) -> list[BenchmarkWorkItem]:
        """Generate workload sequence matching scenario parameters."""
        self._rng = random.Random(config.seed)
        scenario = config.scenario.lower()

        if scenario == "sustained_overload":
            return self._generate_overload(config)
        elif scenario == "burst":
            return self._generate_burst(config)
        elif scenario == "mixed_compute":
            return self._generate_mixed_compute(config)
        elif scenario == "deadline_pressure":
            return self._generate_deadline_pressure(config)
        elif scenario == "multi_tenant":
            return self._generate_multi_tenant(config)
        elif scenario == "failure_recovery":
            return self._generate_failure_recovery(config)
        else:
            return self._generate_normal_load(config)

    def _generate_normal_load(self, config: BenchmarkConfig) -> list[BenchmarkWorkItem]:
        items = []
        now = datetime.now(timezone.utc)
        count = int(config.duration_sec * 50)  # Ingress < capacity
        for i in range(count):
            items.append(self._create_item(i, arrival=i * 0.02, now=now))
        return items

    def _generate_overload(self, config: BenchmarkConfig) -> list[BenchmarkWorkItem]:
        items = []
        now = datetime.now(timezone.utc)
        count = int(config.duration_sec * 300)  # Ingress 300/s vs Capacity 100/s
        for i in range(count):
            items.append(self._create_item(i, arrival=i * (config.duration_sec / count), now=now))
        return items

    def _generate_burst(self, config: BenchmarkConfig) -> list[BenchmarkWorkItem]:
        items = []
        now = datetime.now(timezone.utc)
        # Normal 10s -> Burst 20s -> Normal 10s
        idx = 0
        for t in range(0, int(config.duration_sec)):
            rate = 400 if 10 <= t <= 30 else 30
            for _ in range(rate):
                items.append(self._create_item(idx, arrival=t + self._rng.random(), now=now))
                idx += 1
        return items

    def _generate_mixed_compute(self, config: BenchmarkConfig) -> list[BenchmarkWorkItem]:
        items = []
        now = datetime.now(timezone.utc)
        for i in range(200):
            cost = self._rng.choice([0.1, 0.2, 1.5, 3.0])
            val = self._rng.choice([0.15, 0.3, 0.85, 0.95])
            items.append(self._create_item(i, arrival=i * 0.05, now=now, force_cost=cost, force_val=val))
        return items

    def _generate_deadline_pressure(self, config: BenchmarkConfig) -> list[BenchmarkWorkItem]:
        items = []
        now = datetime.now(timezone.utc)
        for i in range(200):
            ttl = self._rng.choice([1.0, 3.0, 30.0, 300.0])
            items.append(self._create_item(i, arrival=i * 0.05, now=now, force_ttl=ttl))
        return items

    def _generate_multi_tenant(self, config: BenchmarkConfig) -> list[BenchmarkWorkItem]:
        items = []
        now = datetime.now(timezone.utc)
        tenants = ["tenant_alpha", "tenant_beta", "tenant_gamma"]
        for i in range(300):
            t_id = tenants[i % len(tenants)]
            items.append(self._create_item(i, arrival=i * 0.03, now=now, tenant_id=t_id))
        return items

    def _generate_failure_recovery(self, config: BenchmarkConfig) -> list[BenchmarkWorkItem]:
        items = []
        now = datetime.now(timezone.utc)
        for i in range(150):
            items.append(self._create_item(i, arrival=i * 0.04, now=now))
        return items

    def _create_item(
        self,
        idx: int,
        arrival: float,
        now: datetime,
        force_cost: float | None = None,
        force_val: float | None = None,
        force_ttl: float | None = None,
        tenant_id: str = "tenant_bench",
    ) -> BenchmarkWorkItem:
        consequence = force_val if force_val is not None else self._rng.uniform(0.1, 0.95)
        cost = force_cost if force_cost is not None else self._rng.uniform(0.1, 0.5)
        ttl = force_ttl if force_ttl is not None else self._rng.choice([10.0, 60.0, 300.0])
        is_critical = consequence >= 0.8
        work_id = f"work_bench_{idx}"

        event = SignalEvent(
            source_type="benchmark",
            source_id=str(idx),
            tenant_id=tenant_id,
            payload_hash=f"bench_hash_{idx}",
            coalesce_key=f"bench_key_{idx % 10}",
            raw_payload={"bench_idx": idx},
            created_at=now,
            deadline_at=now + timedelta(seconds=ttl),
            severity=SeverityLevel.HIGH if is_critical else SeverityLevel.INFO,
        )

        urgency = self._rng.uniform(0.2, 0.9)
        expected_val = ValueAssessment.compute_expected_value(urgency, 0.9, consequence, event.deadline_at, event.created_at, now)
        val_per_comp = ValueAssessment.compute_value_per_compute(expected_val, cost)

        assessment = ValueAssessment(
            work_item_id=work_id,
            work_item_type="signal",
            urgency=urgency,
            confidence=0.9,
            consequence_of_drop=consequence,
            estimated_compute_cost=cost,
            rationale="Benchmark workload item",
            expected_value=expected_val,
            value_per_compute=val_per_comp,
            deadline=event.deadline_at,
        )

        return BenchmarkWorkItem(
            work_item_id=work_id,
            event=event,
            assessment=assessment,
            arrival_time_sec=arrival,
            is_critical=is_critical,
            estimated_compute_cost=cost,
        )
