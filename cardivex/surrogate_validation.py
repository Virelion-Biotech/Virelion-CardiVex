from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .longitudinal import LongitudinalGroup, longitudinal_domain_series
from .models import Scenario
from .temporal_metrics import trajectory_error


@dataclass(frozen=True)
class SurrogateValidation:
    """Validation summary for one scenario against a held-out observed trajectory."""

    scenario_id: str
    group_id: str
    domain_mae: float
    domain_max_error: float
    temporal_similarity: float
    evaluated_points: int
    evaluated_domains: int
    observed_dataset_ids: tuple[str, ...]

    @property
    def acceptable(self) -> bool:
        return self.evaluated_points > 0 and self.evaluated_domains > 0


def _scenario_series(scenario: Scenario) -> dict[str, tuple[tuple[float, float], ...]]:
    domains = sorted(set().union(*(state.domains.keys() for state in scenario.temporal_profile)))
    return {
        domain: tuple(
            (float(state.relative_time), float(state.domains.get(domain, 0.0).value))
            for state in scenario.temporal_profile
        )
        for domain in domains
    }


def _nearest_observed_value(series: Sequence[tuple[float, float]], time: float) -> float | None:
    if not series:
        return None
    point = min(series, key=lambda item: abs(float(item[0]) - float(time)))
    return float(point[1])


def validate_scenario_against_group(
    scenario: Scenario,
    group: LongitudinalGroup,
    *,
    time_tolerance: float = 0.0,
) -> SurrogateValidation:
    """Compare a generated scenario trajectory with one held-out observed unit."""
    if time_tolerance < 0:
        raise ValueError("time_tolerance must be non-negative")
    predicted = _scenario_series(scenario)
    observed = longitudinal_domain_series(group)

    errors: list[float] = []
    domains = 0
    for domain in sorted(set(predicted) & set(observed)):
        matched = 0
        for time, value in predicted[domain]:
            candidates = [point for point in observed[domain] if abs(float(point[0]) - time) <= time_tolerance]
            if candidates:
                observed_value = min(candidates, key=lambda point: abs(float(point[0]) - time))[1]
            else:
                observed_value = _nearest_observed_value(observed[domain], time)
                if observed_value is None:
                    continue
            errors.append(abs(float(value) - float(observed_value)))
            matched += 1
        if matched:
            domains += 1

    all_errors = tuple(errors)
    mae = sum(all_errors) / len(all_errors) if all_errors else 0.0
    max_error = max(all_errors, default=0.0)
    temporal = trajectory_error(predicted, observed, time_tolerance=time_tolerance)
    similarity = max(0.0, 1.0 - temporal.mae)

    return SurrogateValidation(
        scenario_id=scenario.scenario_id,
        group_id=group.group_id,
        domain_mae=mae,
        domain_max_error=max_error,
        temporal_similarity=similarity,
        evaluated_points=len(all_errors),
        evaluated_domains=domains,
        observed_dataset_ids=group.dataset_ids,
    )


def summarize_surrogate_validation(results: Iterable[SurrogateValidation]) -> dict[str, float | int]:
    """Summarize held-out surrogate validation without pooling experimental units blindly."""
    rows = tuple(results)
    if not rows:
        return {"groups": 0, "mean_domain_mae": 0.0, "mean_temporal_similarity": 0.0}
    return {
        "groups": len(rows),
        "mean_domain_mae": sum(row.domain_mae for row in rows) / len(rows),
        "mean_temporal_similarity": sum(row.temporal_similarity for row in rows) / len(rows),
        "max_group_domain_mae": max(row.domain_mae for row in rows),
    }
