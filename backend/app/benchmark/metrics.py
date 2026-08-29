"""Benchmark Metrics Collector & Comparison Computation.

Provides statistical math functions for calculating percentiles, survival rates, and comparative deltas.
"""

import math
from app.benchmark.models import BenchmarkResult, BenchmarkComparison


class MetricsCollector:
    """Computes empirical math, percentiles, and comparative deltas."""

    @staticmethod
    def calculate_percentile(data: list[float], percentile: float) -> float:
        """Calculate percentile value from a numeric list."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = math.ceil(percentile * len(sorted_data)) - 1
        return sorted_data[max(0, min(idx, len(sorted_data) - 1))]

    @staticmethod
    def compare_results(fifo: BenchmarkResult, ledger: BenchmarkResult) -> BenchmarkComparison:
        """Calculate absolute and relative comparative differences between FIFO and Ledger."""
        abs_diff = {}
        rel_diff = {}

        metrics = [
            ("completed_count", fifo.completed_count, ledger.completed_count),
            ("critical_survival_rate", fifo.critical_survival_rate, ledger.critical_survival_rate),
            ("value_preserved_rate", fifo.value_preserved_rate, ledger.value_preserved_rate),
            ("throughput_items_per_sec", fifo.throughput_items_per_sec, ledger.throughput_items_per_sec),
            ("latency_p95_sec", fifo.latency_p95_sec, ledger.latency_p95_sec),
            ("dropped_value", fifo.dropped_value, ledger.dropped_value),
        ]

        for name, fifo_val, ledger_val in metrics:
            diff = ledger_val - fifo_val
            abs_diff[name] = diff
            if fifo_val != 0:
                rel_diff[name] = (diff / fifo_val) * 100.0
            else:
                rel_diff[name] = 0.0

        return BenchmarkComparison(
            scenario=fifo.scenario,
            seed=fifo.seed,
            fifo_result=fifo,
            ledger_result=ledger,
            absolute_diff=abs_diff,
            relative_diff=rel_diff,
        )
