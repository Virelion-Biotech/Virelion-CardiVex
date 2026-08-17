from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .benchmark_factory import BenchmarkManifest, build_manifest
from .calibration_runner import CalibrationArtifact, compute_artifact_id
from .frozen_scenario import build_scenario_from_frozen_calibration
from .models import Scenario
from .surrogate_validation import validate_scenario_against_group
from .longitudinal import LongitudinalGroup


@dataclass(frozen=True)
class FrozenBenchmark:
    """Benchmark suite whose generated scenarios all inherit one frozen calibration."""

    manifest: BenchmarkManifest
    calibration_artifact_id: str
    scenario_ids: tuple[str, ...]


def build_frozen_benchmark(
    artifact: CalibrationArtifact,
    *,
    condition: str,
    scenario_specs: Sequence[tuple[str, str]],
    target_model: str,
    seed: int = 0,
) -> FrozenBenchmark:
    """Generate a deterministic challenge suite from one verified calibration artifact."""
    if compute_artifact_id(artifact) != artifact.artifact_id:
        raise ValueError("calibration artifact integrity check failed")
    scenarios: list[Scenario] = []
    for index, (scenario_id, name) in enumerate(scenario_specs):
        scenario = build_scenario_from_frozen_calibration(
            artifact,
            condition=condition,
            scenario_id=scenario_id,
            name=name,
            target_model=target_model,
            seed=seed + index,
        )
        scenarios.append(scenario)
    manifest = build_manifest(scenarios, name="cardivex-frozen-challenge-suite", version="0.5.0")
    return FrozenBenchmark(
        manifest=manifest,
        calibration_artifact_id=artifact.artifact_id,
        scenario_ids=manifest.ids(),
    )


def validate_frozen_benchmark_against_groups(
    benchmark: FrozenBenchmark,
    held_out_groups: Sequence[LongitudinalGroup],
    *,
    time_tolerance: float = 0.0,
) -> tuple[object, ...]:
    """Score every frozen scenario against held-out groups without refitting."""
    results: list[object] = []
    for scenario in benchmark.manifest.scenarios:
        for group in held_out_groups:
            results.append(
                validate_scenario_against_group(
                    scenario,
                    group,
                    time_tolerance=time_tolerance,
                    translation_profile=None,
                )
            )
    return tuple(results)
