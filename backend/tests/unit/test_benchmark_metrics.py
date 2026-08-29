"""Unit Tests for Benchmark Metrics Collector.

Validates statistical percentiles, comparison deltas, and zero denominator safety.
"""

from app.benchmark.models import BenchmarkResult
from app.benchmark.metrics import MetricsCollector


def test_percentile_calculation():
    data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p50 = MetricsCollector.calculate_percentile(data, 0.5)
    p95 = MetricsCollector.calculate_percentile(data, 0.95)

    assert p50 == 50.0
    assert p95 == 100.0


def test_comparison_delta_calculation():
    fifo = BenchmarkResult(
        policy="FIFO",
        scenario="overload",
        seed=42,
        completed_count=50,
        critical_survival_rate=0.5,
        value_preserved_rate=0.4,
        throughput_items_per_sec=5.0,
    )
    ledger = BenchmarkResult(
        policy="Ledger",
        scenario="overload",
        seed=42,
        completed_count=90,
        critical_survival_rate=0.9,
        value_preserved_rate=0.8,
        throughput_items_per_sec=9.0,
    )

    comp = MetricsCollector.compare_results(fifo, ledger)
    assert comp.absolute_diff["completed_count"] == 40
    assert comp.relative_diff["critical_survival_rate"] == 80.0
