from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class DomainAttribution:
    domain: str
    baseline: float
    observed: float
    delta: float
    contribution: float


def attribute_domains(
    baseline: Mapping[str, float],
    observed: Mapping[str, float],
    *,
    top_k: int | None = None,
) -> list[DomainAttribution]:
    """Rank domain-level deviations from baseline.

    This is an interpretable diagnostic baseline, not causal inference.
    """
    keys = set(baseline) | set(observed)
    raw = []
    total = 0.0
    for key in keys:
        b = float(baseline.get(key, 0.0))
        x = float(observed.get(key, 0.0))
        delta = x - b
        contribution = abs(delta)
        total += contribution
        raw.append((key, b, x, delta, contribution))

    if total == 0.0:
        results = [DomainAttribution(k, b, x, d, 0.0) for k, b, x, d, _ in raw]
    else:
        results = [
            DomainAttribution(k, b, x, d, c / total)
            for k, b, x, d, c in raw
        ]
    results.sort(key=lambda item: (-item.contribution, item.domain))
    return results if top_k is None else results[: max(0, top_k)]
