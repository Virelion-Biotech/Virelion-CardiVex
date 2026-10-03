from __future__ import annotations

from dataclasses import replace

from .calibration_runner import CalibrationArtifact, compute_artifact_id
from .scenario_builder import ScenarioBuildConfig, build_challenge_scenario


def _verify_artifact(artifact: CalibrationArtifact) -> None:
    expected = compute_artifact_id(artifact)
    if expected != artifact.artifact_id:
        raise ValueError(
            "calibration artifact integrity check failed: "
            f"expected {expected}, found {artifact.artifact_id}"
        )


def build_scenario_from_frozen_calibration(
    artifact: CalibrationArtifact,
    *,
    condition: str,
    scenario_id: str,
    name: str,
    target_model: str,
    config: ScenarioBuildConfig | None = None,
):
    """Generate a downstream phenotype scenario from an immutable calibration artifact.

    No fitting occurs here. The selected empirical profile, correlation structure,
    and temporal profile all come from the frozen development artifact.
    """
    _verify_artifact(artifact)
    matches = [item for item in artifact.condition_calibrations if item.condition == condition]
    if len(matches) != 1:
        raise ValueError(f"condition not uniquely represented in calibration artifact: {condition}")
    selected = matches[0]
    if config is None:
        config = ScenarioBuildConfig()
    else:
        config = replace(config)
    scenario = build_challenge_scenario(
        selected.profile,
        scenario_id=scenario_id,
        name=name,
        target_model=target_model,
        config=config,
        correlation_matrix=selected.correlation if config.use_correlation else None,
        temporal_profile=selected.temporal,
    )
    return replace(
        scenario,
        provenance_sources=tuple(sorted(set(scenario.provenance_sources) | {artifact.dataset_id})),
        provenance_transformations=tuple(
            [f"frozen_calibration:{artifact.artifact_id}"] + list(scenario.provenance_transformations)
        ),
        variation_space={
            **dict(scenario.variation_space),
            "frozen_calibration_artifact": artifact.artifact_id,
        },
    )
