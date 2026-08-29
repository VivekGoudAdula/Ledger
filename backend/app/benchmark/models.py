"""Benchmark Domain Models.

Defines BenchmarkWorkItem, BenchmarkConfig, BenchmarkResult, and BenchmarkComparison models.
"""

from dataclasses import dataclass, field
from typing import Any
from app.domain.models import SignalEvent, ValueAssessment


@dataclass(frozen=True)
class BenchmarkWorkItem:
    """Immutable benchmark work item encapsulating signal event and value assessment."""

    work_item_id: str
    event: SignalEvent
    assessment: ValueAssessment
    arrival_time_sec: float
    is_critical: bool
    estimated_compute_cost: float


@dataclass(frozen=True)
class BenchmarkConfig:
    """Benchmark configuration parameters."""

    scenario: str
    seed: int = 42
    duration_sec: float = 60.0
    capacity_per_sec: float = 100.0
    worker_count: int = 4
    worker_concurrency: int = 2


@dataclass
class BenchmarkResult:
    """Empirical measurements gathered from a benchmark execution run."""

    policy: str
    scenario: str
    seed: int
    completed_count: int = 0
    admitted_count: int = 0
    deferred_count: int = 0
    shed_count: int = 0
    failed_count: int = 0
    throughput_items_per_sec: float = 0.0
    latency_mean_sec: float = 0.0
    latency_p50_sec: float = 0.0
    latency_p95_sec: float = 0.0
    critical_survival_rate: float = 0.0
    value_preserved_rate: float = 0.0
    total_compute_consumed: float = 0.0
    dropped_value: float = 0.0
    deferred_value: float = 0.0
    duplicate_actions: int = 0
    recovery_time_sec: float | None = None
    tenant_fairness_score: float = 1.0


@dataclass
class BenchmarkComparison:
    """Empirical comparison results between FIFO Baseline and Ledger Value-Aware Admission."""

    scenario: str
    seed: int
    fifo_result: BenchmarkResult
    ledger_result: BenchmarkResult
    absolute_diff: dict[str, float] = field(default_factory=dict)
    relative_diff: dict[str, float] = field(default_factory=dict)
