from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Sequence

from .calibration_runner import CalibrationArtifact, compute_artifact_id
from .longitudinal import LongitudinalGroup
from .models import Scenario
from .surrogate_validation import SurrogateValidation, summarize_surrogate_validation, validate_scenario_against_group


@dataclass(frozen=True)
class FrozenValidationRun:
    """Held-out validation performed from an immutable development calibration artifact."""

    artifact_id: str
    held_out_group_count: int
    scenario_count: int
    results: tuple[SurrogateValidation, ...]
    summary: dict[str, float | int]
    clean_split: bool
    run_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "held_out_group_count": self.held_out_group_count,
            "scenario_count": self.scenario_count,
            "results": [asdict(result) for result in self.results],
            "summary": dict(self.summary),
            "clean_split": self.clean_split,
            "run_id": self.run_id,
        }


def _run_id(artifact_id: str, scenario_ids: Sequence[str], group_ids: Sequence[str]) -> str:
    payload = {
        "artifact_id": artifact_id,
        "scenario_ids": sorted(scenario_ids),
        "group_ids": sorted(group_ids),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(canonical).hexdigest()[:16]


def _validate_artifact_integrity(artifact: CalibrationArtifact, held_out_groups: Sequence[LongitudinalGroup]) -> None:
    if not artifact.artifact_id or compute_artifact_id(artifact) != artifact.artifact_id:
        raise ValueError("calibration artifact integrity check failed")

    holdout_ids = {group.group_id for group in held_out_groups}
    declared_holdouts = set(artifact.held_out_group_ids)
    if not holdout_ids:
        raise ValueError("at least one held-out group is required")
    if holdout_ids != declared_holdouts:
        missing = sorted(declared_holdouts - holdout_ids)
        extra = sorted(holdout_ids - declared_holdouts)
        details: list[str] = []
        if missing:
            details.append("missing declared held-out groups: " + ", ".join(missing))
        if extra:
            details.append("unexpected held-out groups: " + ", ".join(extra))
        raise ValueError("held-out groups do not match frozen calibration artifact: " + "; ".join(details))

    development = set(artifact.development_record_ids)
    excluded = set(artifact.excluded_record_ids)
    if development & excluded:
        raise ValueError("calibration artifact contains development/excluded record overlap")

    observed_holdout_records = {
        record.observation_id
        for group in held_out_groups
        for record in group.records
    }
    leaked = development & observed_holdout_records
    if leaked:
        raise ValueError("held-out observations were used during calibration: " + ", ".join(sorted(leaked)))


def run_frozen_validation(
    artifact: CalibrationArtifact,
    scenarios: Sequence[Scenario],
    held_out_groups: Sequence[LongitudinalGroup],
    *,
    time_tolerance: float = 0.0,
) -> FrozenValidationRun:
    """Validate scenarios using only a previously frozen development calibration."""
    if not scenarios:
        raise ValueError("at least one scenario is required")
    if time_tolerance < 0:
        raise ValueError("time_tolerance must be non-negative")
    _validate_artifact_integrity(artifact, held_out_groups)

    # The translation profile comes from the frozen artifact; no fitting occurs here.
    profile = artifact.translation_profile
    results: list[SurrogateValidation] = []
    for scenario in scenarios:
        for group in held_out_groups:
            results.append(
                validate_scenario_against_group(
                    scenario,
                    group,
                    time_tolerance=time_tolerance,
                    translation_profile=profile,
                )
            )

    ordered = tuple(sorted(results, key=lambda item: (item.scenario_id, item.group_id)))
    return FrozenValidationRun(
        artifact_id=artifact.artifact_id,
        held_out_group_count=len(held_out_groups),
        scenario_count=len(scenarios),
        results=ordered,
        summary=summarize_surrogate_validation(ordered),
        clean_split=True,
        run_id=_run_id(
            artifact.artifact_id,
            [scenario.scenario_id for scenario in scenarios],
            [group.group_id for group in held_out_groups],
        ),
    )


def frozen_validation_json(run: FrozenValidationRun) -> str:
    return json.dumps(run.to_dict(), sort_keys=True, indent=2)
