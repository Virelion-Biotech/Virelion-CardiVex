from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .benchmark_factory import BenchmarkManifest, build_manifest
from .calibration_runner import CalibrationArtifact, compute_artifact_id
from .frozen_scenario import build_scenario_from_frozen_calibration
from .longitudinal import LongitudinalGroup
from .models import Scenario
from .scenario_builder import ScenarioBuildConfig
from .surrogate_validation import SurrogateValidation, validate_scenario_against_group


@dataclass(frozen=True)
class FrozenBenchmark:
    """Benchmark suite whose generated scenarios inherit one frozen calibration."""

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
    if not scenario_specs:
        raise ValueError("at least one scenario specification is required")

    scenarios: list[Scenario] = []
    for index, (scenario_id, name) in enumerate(scenario_specs):
        scenarios.append(
            build_scenario_from_frozen_calibration(
                artifact,
                condition=condition,
                scenario_id=scenario_id,
                name=name,
                target_model=target_model,
                config=ScenarioBuildConfig(seed=seed + index),
            )
        )
    manifest = build_manifest(
        scenarios,
        name="cardivex-frozen-challenge-suite",
        version="0.5.0",
    )
    return FrozenBenchmark(
        manifest=manifest,
        calibration_artifact_id=artifact.artifact_id,
        scenario_ids=manifest.ids(),
    )


def validate_frozen_benchmark_against_groups(
    benchmark: FrozenBenchmark,
    artifact: CalibrationArtifact,
    held_out_groups: Sequence[LongitudinalGroup],
    *,
    time_tolerance: float = 0.0,
) -> tuple[SurrogateValidation, ...]:
    """Score every frozen scenario against held-out groups without refitting."""
    if compute_artifact_id(artifact) != artifact.artifact_id:
        raise ValueError("calibration artifact integrity check failed")
    if benchmark.calibration_artifact_id != artifact.artifact_id:
        raise ValueError("benchmark and calibration artifact IDs do not match")
    if not held_out_groups:
        raise ValueError("at least one held-out group is required")

    translation_profile = artifact.translation_profile
    results: list[SurrogateValidation] = []
    for scenario in benchmark.manifest.scenarios:
        markers = {
            marker.split(":", 1)[1]
            for marker in scenario.provenance_transformations
            if marker.startswith("frozen_calibration:")
        }
        if artifact.artifact_id not in markers:
            raise ValueError(
                f"scenario {scenario.scenario_id} is not linked to calibration artifact {artifact.artifact_id}"
            )
        for group in held_out_groups:
            results.append(
                validate_scenario_against_group(
                    scenario,
                    group,
                    time_tolerance=time_tolerance,
                    translation_profile=translation_profile,
                )
            )
    return tuple(sorted(results, key=lambda item: (item.scenario_id, item.group_id)))
