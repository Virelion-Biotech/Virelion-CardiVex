from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence

from .longitudinal import LongitudinalGroup, validate_disjoint_longitudinal_groups
from .models import Scenario
from .surrogate_validation import SurrogateValidation, summarize_surrogate_validation, validate_scenario_against_group
from .translation import TranslationProfile


@dataclass(frozen=True)
class SurrogateValidationRun:
    """Reproducible validation result for disjoint longitudinal held-out units."""

    run_id: str
    development_group_count: int
    held_out_group_count: int
    scenario_count: int
    results: tuple[SurrogateValidation, ...]
    summary: Mapping[str, float | int]
    clean_split: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "development_group_count": self.development_group_count,
            "held_out_group_count": self.held_out_group_count,
            "scenario_count": self.scenario_count,
            "results": [asdict(result) for result in self.results],
            "summary": dict(self.summary),
            "clean_split": self.clean_split,
        }


def _run_id(
    scenarios: Sequence[Scenario],
    development_groups: Sequence[LongitudinalGroup],
    held_out_groups: Sequence[LongitudinalGroup],
) -> str:
    payload = {
        "scenarios": [scenario.scenario_id for scenario in scenarios],
        "development_groups": [group.group_id for group in development_groups],
        "held_out_groups": [group.group_id for group in held_out_groups],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()[:16]


def run_surrogate_validation(
    scenarios: Sequence[Scenario],
    development_groups: Sequence[LongitudinalGroup],
    held_out_groups: Sequence[LongitudinalGroup],
    *,
    time_tolerance: float = 0.0,
    translation_profile: TranslationProfile | None = None,
) -> SurrogateValidationRun:
    """Evaluate development-derived scenarios on disjoint held-out experimental units."""
    if not scenarios:
        raise ValueError("at least one scenario is required")
    if not development_groups:
        raise ValueError("at least one development group is required")
    if not held_out_groups:
        raise ValueError("at least one held-out group is required")
    overlap = validate_disjoint_longitudinal_groups(development_groups, held_out_groups)
    if overlap:
        raise ValueError("development and held-out experimental units overlap: " + ", ".join(overlap))

    results: list[SurrogateValidation] = []
    for scenario in scenarios:
        for group in held_out_groups:
            results.append(
                validate_scenario_against_group(
                    scenario,
                    group,
                    time_tolerance=time_tolerance,
                    translation_profile=translation_profile,
                )
            )

    ordered = tuple(sorted(results, key=lambda result: (result.scenario_id, result.group_id)))
    return SurrogateValidationRun(
        run_id=_run_id(scenarios, development_groups, held_out_groups),
        development_group_count=len(development_groups),
        held_out_group_count=len(held_out_groups),
        scenario_count=len(scenarios),
        results=ordered,
        summary=summarize_surrogate_validation(ordered),
        clean_split=True,
    )


def surrogate_validation_json(run: SurrogateValidationRun) -> str:
    return json.dumps(run.to_dict(), sort_keys=True, indent=2)