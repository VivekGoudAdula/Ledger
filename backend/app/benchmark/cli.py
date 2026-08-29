"""Benchmark CLI Tool.

Executes scientific comparison runs and displays empirical tabular metrics.

Usage:
    python -m app.benchmark.cli compare --scenario sustained_overload --seed 42
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.benchmark.runner import BenchmarkRunner


def run_cli() -> None:
    """CLI entry point for benchmark commands."""
    parser = argparse.ArgumentParser(description="Ledger Controlled Benchmark Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare_parser = subparsers.add_parser("compare", help="Compare FIFO baseline vs Ledger admission")
    compare_parser.add_argument("--scenario", type=str, default="sustained_overload", help="Scenario name")
    compare_parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    compare_parser.add_argument("--json", action="store_true", help="Output JSON results")

    args = parser.parse_args()

    if args.command == "compare":
        runner = BenchmarkRunner()
        comp = runner.run_comparison(scenario=args.scenario, seed=args.seed)

        if args.json:
            out = {
                "scenario": comp.scenario,
                "seed": comp.seed,
                "fifo": comp.fifo_result.__dict__,
                "ledger": comp.ledger_result.__dict__,
                "absolute_diff": comp.absolute_diff,
                "relative_diff": comp.relative_diff,
            }
            print(json.dumps(out, indent=2))
        else:
            print("\n" + "=" * 70)
            print(f" LEDGER BENCHMARK ENGINE — COMPARATIVE RESULTS (SEED: {comp.seed}) ")
            print("=" * 70)
            print(f"Scenario: {comp.scenario}\n")
            print(f"{'METRIC':<30} | {'FIFO BASELINE':<15} | {'LEDGER VALUE':<15} | {'DIFF':<10}")
            print("-" * 75)
            print(f"{'Admitted Count':<30} | {comp.fifo_result.admitted_count:<15} | {comp.ledger_result.admitted_count:<15} | {comp.ledger_result.admitted_count - comp.fifo_result.admitted_count:+d}")
            print(f"{'Critical Survival Rate':<30} | {comp.fifo_result.critical_survival_rate*100:14.1f}% | {comp.ledger_result.critical_survival_rate*100:14.1f}% | {comp.relative_diff['critical_survival_rate']:+6.1f}%")
            print(f"{'Value Preserved Rate':<30} | {comp.fifo_result.value_preserved_rate*100:14.1f}% | {comp.ledger_result.value_preserved_rate*100:14.1f}% | {comp.relative_diff['value_preserved_rate']:+6.1f}%")
            print(f"{'Throughput (items/sec)':<30} | {comp.fifo_result.throughput_items_per_sec:14.2f} | {comp.ledger_result.throughput_items_per_sec:14.2f} | {comp.relative_diff['throughput_items_per_sec']:+6.1f}%")
            print(f"{'P95 Latency (sec)':<30} | {comp.fifo_result.latency_p95_sec:14.3f} | {comp.ledger_result.latency_p95_sec:14.3f} | {comp.relative_diff['latency_p95_sec']:+6.1f}%")
            print(f"{'Dropped Value':<30} | {comp.fifo_result.dropped_value:14.2f} | {comp.ledger_result.dropped_value:14.2f} | {comp.absolute_diff['dropped_value']:+6.2f}")
            print(f"{'Duplicate Actions':<30} | {comp.fifo_result.duplicate_actions:<15} | {comp.ledger_result.duplicate_actions:<15} | {comp.ledger_result.duplicate_actions - comp.fifo_result.duplicate_actions:+d}")
            print("=" * 75)


if __name__ == "__main__":
    run_cli()
