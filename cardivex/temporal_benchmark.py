from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .longitudinal import LongitudinalGroup, validate_disjoint_longitudinal_groups
from .temporal_surrogate import TemporalSurrogate


@dataclass(frozen=True)
class TemporalBenchmark:
    """Held-out comparison of a temporal surrogate against persistence."""

    model_mean_absolute_error: float
    persistence_mean_absolute_error: float
    improvement_vs_persistence: float
    transition_count: int
    evaluated_domain_values: int


def _evaluate_errors(
    model: TemporalSurrogate,
    groups: Sequence[LongitudinalGroup],
) -> tuple[list[float], list[float], int]:
    model_errors: list[float] = []
    persistence_errors: list[float] = []
    transitions = 0
    for group in groups:
        records = group.records
        for current, nxt in zip(records, records[1:]):
            prediction = model.predict_next(
                current.state.domain_scores,
                delta=float(nxt.time - current.time),
            )
            for domain in model.domains:
                observed = float(nxt.state.domain_scores.get(domain, 0.0))
                model_errors.append(abs(prediction[domain] - observed))
                persistence = float(current.state.domain_scores.get(domain, 0.0))
                persistence_errors.append(abs(persistence - observed))
            transitions += 1
    return model_errors, persistence_errors, transitions


def benchmark_temporal_surrogate(
    model: TemporalSurrogate,
    held_out_groups: Sequence[LongitudinalGroup],
    *,
    development_groups: Sequence[LongitudinalGroup] = (),
) -> TemporalBenchmark:
    """Compare held-out next-state prediction with a persistence baseline.

    Persistence predicts that every domain remains at its current value. This
    baseline is intentionally simple and does not access development data.
    """
    if development_groups:
        overlap = validate_disjoint_longitudinal_groups(development_groups, held_out_groups)
        if overlap:
            raise ValueError("development and held-out groups overlap: " + ", ".join(overlap))
    model_errors, persistence_errors, transitions = _evaluate_errors(model, held_out_groups)
    if not model_errors:
        raise ValueError("held-out groups contain no evaluable transitions")
    model_mae = sum(model_errors) / len(model_errors)
    persistence_mae = sum(persistence_errors) / len(persistence_errors)
    improvement = 0.0 if persistence_mae == 0.0 else (persistence_mae - model_mae) / persistence_mae
    return TemporalBenchmark(
        model_mean_absolute_error=model_mae,
        persistence_mean_absolute_error=persistence_mae,
        improvement_vs_persistence=improvement,
        transition_count=transitions,
        evaluated_domain_values=len(model_errors),
    )
