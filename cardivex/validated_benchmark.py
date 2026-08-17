from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Mapping, Sequence

from .features import CardiacState
from .longitudinal import LongitudinalGroup, validate_disjoint_longitudinal_groups
from .models import Scenario
from .suite import BenchmarkRun, run_benchmark_suite
from .surrogate_runner import SurrogateValidationRun, run_surrogate_validation
from .translation import TranslationProfile


@dataclass(frozen=True)
class ValidatedBenchmarkRun:
    """Combined defensive benchmark and held-out surrogate-validation result."""

    benchmark: BenchmarkRun
    surrogate_validation: SurrogateValidationRun
    validation_policy: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark": self.benchmark.to_dict(),
            "surrogate_validation": self.surrogate_validation.to_dict(),
            "validation_policy": dict(self.validation_policy),
        }


def run_validated_benchmark(
    scenarios: Sequence[Scenario],
    *,
    baseline: CardiacState,
    known_states: Sequence[CardiacState],
    development_groups: Sequence[LongitudinalGroup],
    held_out_groups: Sequence[LongitudinalGroup],
    translation_profile: TranslationProfile | None = None,
    reference_split: str = "development",
    time_tolerance: float = 0.0,
    name: str = "cardivex-validated-benchmark",
    version: str = "0.1.0",
) -> ValidatedBenchmarkRun:
    """Run defensive evaluation plus disjoint held-out surrogate validation."""
    overlap = validate_disjoint_longitudinal_groups(development_groups, held_out_groups)
    if overlap:
        raise ValueError("development and held-out experimental units overlap: " + ", ".join(overlap))

    benchmark = run_benchmark_suite(
        scenarios,
        baseline=baseline,
        known_states=known_states,
        reference_split=reference_split,
        name=name,
        version=version,
    )
    surrogate = run_surrogate_validation(
        scenarios,
        development_groups,
        held_out_groups,
        time_tolerance=time_tolerance,
        translation_profile=translation_profile,
    )
    policy = {
        "reference_split": reference_split,
        "time_tolerance": time_tolerance,
        "held_out_units_disjoint": True,
        "surrogate_validation_is_independent_of_defensive_scoring": True,
    }
    return ValidatedBenchmarkRun(benchmark=benchmark, surrogate_validation=surrogate, validation_policy=policy)


def validated_benchmark_json(run: ValidatedBenchmarkRun) -> str:
    return json.dumps(run.to_dict(), sort_keys=True, indent=2)
