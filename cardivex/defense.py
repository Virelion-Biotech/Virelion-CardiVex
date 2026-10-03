from __future__ import annotations

from math import sqrt
from typing import Mapping


def abnormality_score(
    baseline: Mapping[str, float],
    observed: Mapping[str, float],
    *,
    weights: Mapping[str, float] | None = None,
) -> float:
    """Return a normalized distance from baseline across shared domains."""
    keys = set(baseline) | set(observed)
    if not keys:
        raise ValueError("baseline and observed cannot both be empty")
    weights = weights or {}
    weighted = []
    total_weight = 0.0
    for key in keys:
        b = float(baseline.get(key, 0.0))
        x = float(observed.get(key, 0.0))
        w = float(weights.get(key, 1.0))
        if w < 0:
            raise ValueError("weights must be non-negative")
        weighted.append(w * (x - b) ** 2)
        total_weight += w
    return 0.0 if total_weight == 0 else min(1.0, sqrt(sum(weighted) / total_weight))


def nearest_state_distance(
    query: Mapping[str, float],
    reference_states: list[Mapping[str, float]],
) -> float:
    """Distance to the nearest known phenotype state; a simple OOD baseline."""
    if not reference_states:
        raise ValueError("at least one reference state is required")
    return min(abnormality_score(state, query) for state in reference_states)


def rescue_score(
    baseline: Mapping[str, float],
    challenged: Mapping[str, float],
    treated: Mapping[str, float],
) -> float:
    """Measure movement from challenged state back toward baseline."""
    challenge_distance = abnormality_score(baseline, challenged)
    treated_distance = abnormality_score(baseline, treated)
    if challenge_distance == 0:
        return 1.0 if treated_distance == 0 else 0.0
    return max(-1.0, min(1.0, (challenge_distance - treated_distance) / challenge_distance))
