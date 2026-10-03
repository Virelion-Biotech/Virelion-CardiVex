from __future__ import annotations

from math import sqrt
from typing import Mapping, Sequence


def normalized_distance(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    keys = set(a) | set(b)
    if not keys:
        raise ValueError("states cannot both be empty")
    return min(1.0, sqrt(sum((float(a.get(k, 0.0)) - float(b.get(k, 0.0))) ** 2 for k in keys) / len(keys)))


def novelty_margin(candidate: Mapping[str, float], references: Sequence[Mapping[str, float]]) -> float:
    if not references:
        raise ValueError("at least one reference is required")
    nearest = min(normalized_distance(candidate, ref) for ref in references)
    return nearest


def is_novel(candidate: Mapping[str, float], references: Sequence[Mapping[str, float]], *, threshold: float = 0.35) -> bool:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    return novelty_margin(candidate, references) >= threshold
