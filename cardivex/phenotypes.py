from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean, stdev
from typing import Iterable, Mapping

from .ingest import IngestRecord


@dataclass(frozen=True)
class DomainDistribution:
    mean: float
    std: float
    minimum: float
    maximum: float
    count: int


@dataclass(frozen=True)
class EmpiricalPhenotypeProfile:
    condition: str
    domains: Mapping[str, DomainDistribution]
    sample_count: int
    source_dataset_ids: tuple[str, ...]
    feature_contract: str = "cardivex-v1"

    def center(self) -> dict[str, float]:
        return {name: stats.mean for name, stats in self.domains.items()}

    def scale(self) -> dict[str, float]:
        return {name: max(stats.std, 1e-6) for name, stats in self.domains.items()}


def _distribution(values: list[float]) -> DomainDistribution:
    if not values:
        raise ValueError("cannot summarize empty values")
    return DomainDistribution(
        mean=mean(values),
        std=stdev(values) if len(values) > 1 else 0.0,
        minimum=min(values),
        maximum=max(values),
        count=len(values),
    )


def fit_empirical_profile(
    records: Iterable[IngestRecord],
    *,
    condition: str,
) -> EmpiricalPhenotypeProfile:
    selected = [r for r in records if r.condition == condition]
    if not selected:
        raise ValueError(f"no records available for condition: {condition}")
    domains: dict[str, list[float]] = {}
    for record in selected:
        for name, value in record.state.domain_scores.items():
            domains.setdefault(name, []).append(float(value))
    if not domains:
        raise ValueError("selected observations contain no domain scores")
    return EmpiricalPhenotypeProfile(
        condition=condition,
        domains={name: _distribution(values) for name, values in sorted(domains.items())},
        sample_count=len(selected),
        source_dataset_ids=tuple(sorted({r.dataset_id for r in selected})),
    )


def profile_distance(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    keys = set(a) | set(b)
    if not keys:
        raise ValueError("profiles cannot both be empty")
    return min(1.0, sqrt(mean((float(a.get(k, 0.0)) - float(b.get(k, 0.0))) ** 2 for k in keys)))
