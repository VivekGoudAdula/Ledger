"""Benchmark API Route.

Exposes POST /api/v1/benchmark/run to trigger virtual execution simulation comparisons (FIFO vs Ledger).
"""

from typing import Any
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.benchmark.models import BenchmarkConfig
from app.benchmark.workload import WorkloadGenerator
from app.benchmark.engine import VirtualExecutionEngine
from app.benchmark.policies import FIFOPolicy, LedgerPolicyAdapter

router = APIRouter(prefix="/api/v1/benchmark", tags=["Benchmark"])


class BenchmarkRunResponse(BaseModel):
    scenario: str
    workload_size: int
    seed: int
    capacity_per_sec: float
    fifo: dict[str, Any]
    ledger: dict[str, Any]
    comparison: dict[str, Any]


@router.post("/run", response_model=BenchmarkRunResponse, summary="Run Benchmark Comparison (FIFO vs Ledger)")
async def run_benchmark(
    scenario: str = Query(default="sustained_overload"),
    size: int = Query(default=100),
    seed: int = Query(default=42),
    capacity: float = Query(default=10.0),
) -> BenchmarkRunResponse:
    """Run virtual simulation comparison of FIFO vs Ledger under specified scenario."""
    duration = max(10.0, size / 300.0) if scenario == "sustained_overload" else 10.0
    config = BenchmarkConfig(
        scenario=scenario,
        duration_sec=duration,
        capacity_per_sec=capacity,
        seed=seed,
    )

    workload = WorkloadGenerator(seed=seed).generate_workload(config)
    if size and len(workload) > size:
        workload = workload[:size]

    engine = VirtualExecutionEngine()

    fifo_res = engine.run_simulation(workload, FIFOPolicy(), config)
    ledger_res = engine.run_simulation(workload, LedgerPolicyAdapter(), config)

    def res_to_dict(res: Any) -> dict[str, Any]:
        unhandled_val = round(res.dropped_value + res.deferred_value, 2)
        return {
            "completed": res.completed_count,
            "admitted": res.admitted_count,
            "deferred": res.deferred_count,
            "shed": res.shed_count,
            "throughput": round(res.throughput_items_per_sec, 2),
            "mean_latency_sec": round(res.latency_mean_sec, 4),
            "p95_latency_sec": round(res.latency_p95_sec, 4),
            "critical_survival_rate": round(res.critical_survival_rate * 100, 1),
            "value_preserved_rate": round(res.value_preserved_rate * 100, 1),
            "dropped_value": round(res.dropped_value, 2),
            "deferred_value": round(res.deferred_value, 2),
            "unhandled_value": unhandled_val,
        }

    crit_delta = round((ledger_res.critical_survival_rate - fifo_res.critical_survival_rate) * 100, 1)
    val_delta = round((ledger_res.value_preserved_rate - fifo_res.value_preserved_rate) * 100, 1)
    fifo_unhandled = round(fifo_res.dropped_value + fifo_res.deferred_value, 2)
    ledger_unhandled = round(ledger_res.dropped_value + ledger_res.deferred_value, 2)
    unhandled_delta = round(ledger_unhandled - fifo_unhandled, 2)

    return BenchmarkRunResponse(
        scenario=scenario,
        workload_size=len(workload),
        seed=seed,
        capacity_per_sec=capacity,
        fifo=res_to_dict(fifo_res),
        ledger=res_to_dict(ledger_res),
        comparison={
            "critical_survival_delta_pct": crit_delta,
            "value_preserved_delta_pct": val_delta,
            "dropped_value_delta": unhandled_delta,
            "fifo_unhandled_value": fifo_unhandled,
            "ledger_unhandled_value": ledger_unhandled,
        },
    )
