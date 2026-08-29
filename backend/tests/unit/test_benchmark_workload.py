"""Unit Tests for Workload Generator Reproducibility.

Validates that workload generation with identical seeds produces identical workloads,
and different seeds produce different workloads.
"""

from app.benchmark.models import BenchmarkConfig
from app.benchmark.workload import WorkloadGenerator


def test_seed_reproducibility():
    config1 = BenchmarkConfig(scenario="sustained_overload", seed=42)
    gen1 = WorkloadGenerator(seed=42)
    workload1 = gen1.generate_workload(config1)

    config2 = BenchmarkConfig(scenario="sustained_overload", seed=42)
    gen2 = WorkloadGenerator(seed=42)
    workload2 = gen2.generate_workload(config2)

    assert len(workload1) == len(workload2)
    for w1, w2 in zip(workload1, workload2):
        assert w1.work_item_id == w2.work_item_id
        assert w1.arrival_time_sec == w2.arrival_time_sec
        assert w1.assessment.consequence_of_drop == w2.assessment.consequence_of_drop


def test_different_seeds_produce_different_workloads():
    config1 = BenchmarkConfig(scenario="sustained_overload", seed=42)
    workload1 = WorkloadGenerator().generate_workload(config1)

    config2 = BenchmarkConfig(scenario="sustained_overload", seed=99)
    workload2 = WorkloadGenerator().generate_workload(config2)

    assert workload1[0].assessment.consequence_of_drop != workload2[0].assessment.consequence_of_drop
