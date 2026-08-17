from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Mapping, Sequence

from .longitudinal import LongitudinalGroup, validate_disjoint_longitudinal_groups


@dataclass(frozen=True)
class TemporalSurrogateSpec:
    """Deterministic specification for the baseline temporal surrogate."""

    model_id: str = "temporal-linear-baseline"
    model_version: str = "0.1.0"
    learning_rate: float = 0.05
    epochs: int = 800
    l2: float = 1e-3
    include_time_delta: bool = True


@dataclass(frozen=True)
class TemporalSurrogate:
    """Multi-output linear next-state predictor fitted only on development groups."""

    spec: TemporalSurrogateSpec
    domains: tuple[str, ...]
    feature_mean: tuple[float, ...]
    feature_scale: tuple[float, ...]
    weights: tuple[tuple[float, ...], ...]

    def _features(self, current: Mapping[str, float], delta: float) -> tuple[float, ...]:
        values = [float(current.get(domain, 0.0)) for domain in self.domains]
        if self.spec.include_time_delta:
            values.append(float(delta))
        scaled = [
            (value - mean) / scale if scale else value - mean
            for value, mean, scale in zip(values, self.feature_mean, self.feature_scale)
        ]
        return (1.0, *scaled)

    def predict_next(self, current: Mapping[str, float], *, delta: float) -> dict[str, float]:
        x = self._features(current, delta)
        return {
            domain: max(0.0, min(1.0, sum(weight * feature for weight, feature in zip(row, x))))
            for domain, row in zip(self.domains, self.weights)
        }


def _pairs(groups: Sequence[LongitudinalGroup]) -> tuple[tuple[dict[str, float], float, dict[str, float]], ...]:
    pairs: list[tuple[dict[str, float], float, dict[str, float]]] = []
    for group in groups:
        records = group.records
        for current, nxt in zip(records, records[1:]):
            delta = float(nxt.time - current.time)
            if delta <= 0:
                raise ValueError(f"non-positive time delta in group {group.group_id}")
            domains = sorted(set(current.state.domain_scores) | set(nxt.state.domain_scores))
            x = {domain: float(current.state.domain_scores.get(domain, 0.0)) for domain in domains}
            y = {domain: float(nxt.state.domain_scores.get(domain, 0.0)) for domain in domains}
            pairs.append((x, delta, y))
    if not pairs:
        raise ValueError("at least one longitudinal transition is required")
    return tuple(pairs)


def fit_temporal_surrogate(
    development_groups: Sequence[LongitudinalGroup],
    *,
    spec: TemporalSurrogateSpec | None = None,
) -> TemporalSurrogate:
    """Fit a transparent next-state predictor using development groups only.

    Training is performed on observed consecutive transitions; no held-out groups
    are accessed by this function.
    """
    spec = spec or TemporalSurrogateSpec()
    if spec.learning_rate <= 0 or spec.epochs <= 0 or spec.l2 < 0:
        raise ValueError("learning_rate and epochs must be positive; l2 must be non-negative")
    pairs = _pairs(development_groups)
    domains = tuple(sorted(set().union(*(pair[2].keys() for pair in pairs))))
    raw_features = []
    targets = []
    for current, delta, target in pairs:
        values = [float(current.get(domain, 0.0)) for domain in domains]
        if spec.include_time_delta:
            values.append(delta)
        raw_features.append(values)
        targets.append([float(target.get(domain, 0.0)) for domain in domains])

    means = [sum(row[i] for row in raw_features) / len(raw_features) for i in range(len(raw_features[0]))]
    scales = []
    for i, mean in enumerate(means):
        variance = sum((row[i] - mean) ** 2 for row in raw_features) / max(1, len(raw_features) - 1)
        scales.append(sqrt(variance) or 1.0)
    x_rows = [[1.0] + [(value - mean) / scale for value, mean, scale in zip(row, means, scales)] for row in raw_features]

    weight_rows = [[0.0 for _ in x_rows[0]] for _ in domains]
    n = float(len(x_rows))
    for _ in range(spec.epochs):
        gradients = [[0.0 for _ in row] for row in weight_rows]
        for x, y in zip(x_rows, targets):
            predictions = [sum(weight * feature for weight, feature in zip(row, x)) for row in weight_rows]
            for output_index, (prediction, target) in enumerate(zip(predictions, y)):
                error = prediction - target
                for feature_index, feature in enumerate(x):
                    gradients[output_index][feature_index] += (2.0 / n) * error * feature
        for output_index, row in enumerate(weight_rows):
            for feature_index in range(1, len(row)):
                gradients[output_index][feature_index] += 2.0 * spec.l2 * row[feature_index]
            for feature_index in range(len(row)):
                row[feature_index] -= spec.learning_rate * gradients[output_index][feature_index]

    return TemporalSurrogate(
        spec=spec,
        domains=domains,
        feature_mean=tuple(means),
        feature_scale=tuple(scales),
        weights=tuple(tuple(row) for row in weight_rows),
    )


def evaluate_temporal_surrogate(
    model: TemporalSurrogate,
    held_out_groups: Sequence[LongitudinalGroup],
    *,
    development_groups: Sequence[LongitudinalGroup] = (),
) -> Mapping[str, float]:
    """Evaluate next-state MAE on held-out groups, with optional leakage assertion."""
    if development_groups:
        overlap = validate_disjoint_longitudinal_groups(development_groups, held_out_groups)
        if overlap:
            raise ValueError("development and held-out groups overlap: " + ", ".join(overlap))
    absolute_errors: list[float] = []
    transition_count = 0
    for group in held_out_groups:
        records = group.records
        for current, nxt in zip(records, records[1:]):
            prediction = model.predict_next(current.state.domain_scores, delta=nxt.time - current.time)
            for domain in model.domains:
                absolute_errors.append(abs(prediction[domain] - float(nxt.state.domain_scores.get(domain, 0.0))))
            transition_count += 1
    if not absolute_errors:
        raise ValueError("held-out groups contain no evaluable transitions")
    return {
        "mean_absolute_error": sum(absolute_errors) / len(absolute_errors),
        "max_absolute_error": max(absolute_errors),
        "transition_count": float(transition_count),
        "evaluated_domain_values": float(len(absolute_errors)),
    }
