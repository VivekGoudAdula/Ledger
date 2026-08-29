"""Benchmark Runner.

Orchestrates workload generation, executes FIFO and Ledger policies over identical workload,
and constructs scientific BenchmarkComparison results.
"""

from app.benchmark.models import BenchmarkConfig, BenchmarkComparison
from app.benchmark.workload import WorkloadGenerator
from app.benchmark.policies import FIFOPolicy, LedgerPolicyAdapter
from app.benchmark.engine import VirtualExecutionEngine
from app.benchmark.metrics import MetricsCollector


class BenchmarkRunner:
    """Orchestrates controlled benchmark comparisons under identical workloads."""

    def __init__(self, engine: VirtualExecutionEngine | None = None) -> None:
        self._engine = engine or VirtualExecutionEngine()

    def run_comparison(self, scenario: str = "sustained_overload", seed: int = 42) -> BenchmarkComparison:
        """Run scientific comparison between FIFO baseline and Ledger admission over identical workload."""
        config = BenchmarkConfig(scenario=scenario, seed=seed)
        generator = WorkloadGenerator(seed=seed)

        # Step 1: Generate ONCE the immutable workload sequence
        workload = generator.generate_workload(config)

        # Step 2: Execute FIFO Baseline Policy
        fifo_policy = FIFOPolicy()
        fifo_result = self._engine.run_simulation(workload, fifo_policy, config)

        # Step 3: Execute Ledger Value-Aware Policy over EXACT SAME workload
        ledger_policy = LedgerPolicyAdapter()
        ledger_result = self._engine.run_simulation(workload, ledger_policy, config)

        # Step 4: Compute Empirical Comparative Deltas
        return MetricsCollector.compare_results(fifo_result, ledger_result)
