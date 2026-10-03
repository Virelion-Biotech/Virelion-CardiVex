from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class CalibrationBand:
    mean: float
    lower: float
    upper: float
    count: int


def weighted_mean(values: Sequence[float], weights: Sequence[float] | None = None) -> float:
    if not values:
        raise ValueError("values cannot be empty")
    if weights is None:
        return sum(float(v) for v in values) / len(values)
    if len(values) != len(weights) or not weights:
        raise ValueError("values and weights must have equal non-zero length")
    total = sum(float(w) for w in weights)
    if total <= 0:
        raise ValueError("weights must have positive total")
    return sum(float(v) * float(w) for v, w in zip(values, weights)) / total


def uncertainty_band(values: Sequence[float], *, z: float = 1.96) -> CalibrationBand:
    """Return a simple normal-approximation uncertainty band over bounded scores."""
    if not values:
        raise ValueError("values cannot be empty")
    if z <= 0:
        raise ValueError("z must be positive")
    mean = weighted_mean(values)
    if len(values) == 1:
        half = 0.0
    else:
        centered = [(float(v) - mean) ** 2 for v in values]
        sd = sqrt(sum(centered) / (len(values) - 1))
        half = z * sd / sqrt(len(values))
    return CalibrationBand(round(mean, 12), round(max(0.0, mean - half), 12), round(min(1.0, mean + half), 12), len(values))


def domain_uncertainty(domain_scores: Iterable[Mapping[str, float]]) -> dict[str, CalibrationBand]:
    rows = list(domain_scores)
    if not rows:
        raise ValueError("domain_scores cannot be empty")
    domains = sorted(set().union(*(row.keys() for row in rows)))
    return {domain: uncertainty_band([float(row.get(domain, 0.0)) for row in rows]) for domain in domains}


def scenario_calibration_error(
    predicted: Mapping[str, float],
    observed: Mapping[str, float],
) -> dict[str, float]:
    keys = sorted(set(predicted) | set(observed))
    if not keys:
        raise ValueError("predicted and observed cannot both be empty")
    errors = {key: round(abs(float(predicted.get(key, 0.0)) - float(observed.get(key, 0.0))), 12) for key in keys}
    errors["mae"] = round(sum(errors.values()) / len(keys), 12)
    errors["max_error"] = max(errors.values())
    return errors
