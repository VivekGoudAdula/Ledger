"""Integration Tests for Benchmark Comparison Runner.

Verifies scientific comparison execution across sustained overload, burst, mixed compute,
and failure recovery scenarios.
"""

from app.benchmark.runner import BenchmarkRunner


def test_benchmark_runner_sustained_overload():
    runner = BenchmarkRunner()
    comp = runner.run_comparison(scenario="sustained_overload", seed=42)

    assert comp.scenario == "sustained_overload"
    assert comp.seed == 42
    assert comp.fifo_result.admitted_count >= 0
    assert comp.ledger_result.admitted_count >= 0
    assert comp.fifo_result.completed_count >= 0
    assert comp.ledger_result.completed_count >= 0
    assert "critical_survival_rate" in comp.relative_diff
    assert "value_preserved_rate" in comp.relative_diff


def test_benchmark_runner_all_scenarios():
    runner = BenchmarkRunner()
    scenarios = ["normal_load", "burst", "mixed_compute", "deadline_pressure", "multi_tenant", "failure_recovery"]

    for sc in scenarios:
        comp = runner.run_comparison(scenario=sc, seed=42)
        assert comp.fifo_result.completed_count >= 0
        assert comp.ledger_result.completed_count >= 0
        assert comp.fifo_result.policy == "FIFO Baseline"
        assert comp.ledger_result.policy == "Ledger Value-Aware"
