from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Mapping

from .ingest import IngestRecord
from .models import DomainValue, ScenarioState


@dataclass(frozen=True)
class TemporalPoint:
    relative_time: float
    domains: Mapping[str, DomainValue]
    count: int


@dataclass(frozen=True)
class EmpiricalTemporalProfile:
    condition: str
    points: tuple[TemporalPoint, ...]
    source_dataset_ids: tuple[str, ...]

    @property
    def domain_names(self) -> tuple[str, ...]:
        return tuple(sorted(set().union(*(point.domains.keys() for point in self.points))))


def _band(values: list[float]) -> tuple[float, float]:
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, 0.0
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return mean, sqrt(variance / len(values))


def fit_temporal_profile(
    records: Iterable[IngestRecord],
    *,
    condition: str,
    normalize_time: bool = True,
) -> EmpiricalTemporalProfile:
    """Fit an empirical downstream phenotype trajectory from processed observations.

    The fit is deliberately descriptive: it summarizes observed domain behavior
    over time and does not infer a causal mechanism or initiating procedure.
    """
    selected = [record for record in records if record.condition == condition]
    if not selected:
        raise ValueError(f"no records found for condition: {condition}")

    raw_times = sorted({float(record.time) for record in selected})
    if normalize_time:
        t_min, t_max = min(raw_times), max(raw_times)
        denominator = t_max - t_min
    else:
        t_min, denominator = 0.0, 1.0

    grouped: dict[float, list[IngestRecord]] = {time: [] for time in raw_times}
    for record in selected:
        grouped[float(record.time)].append(record)

    points: list[TemporalPoint] = []
    for raw_time in raw_times:
        rows = grouped[raw_time]
        domains = sorted(set().union(*(row.state.domain_scores.keys() for row in rows)))
        values: dict[str, DomainValue] = {}
        for domain in domains:
            observations = [float(row.state.domain_scores.get(domain, 0.0)) for row in rows]
            mean, sem = _band(observations)
            values[domain] = DomainValue(
                value=max(0.0, min(1.0, mean)),
                uncertainty=max(0.0, min(1.0, sem)),
                evidence_status="observed",
            )
        relative_time = 0.0 if denominator == 0 else (raw_time - t_min) / denominator
        points.append(TemporalPoint(relative_time=relative_time, domains=values, count=len(rows)))

    return EmpiricalTemporalProfile(
        condition=condition,
        points=tuple(points),
        source_dataset_ids=tuple(sorted({record.dataset_id for record in selected})),
    )


def materialize_trajectory(
    profile: EmpiricalTemporalProfile,
    *,
    severity_scale: float = 1.0,
    time_scale: float = 1.0,
    time_offset: float = 0.0,
    evidence_status: str = "extrapolated",
) -> tuple[ScenarioState, ...]:
    """Convert an empirical trajectory into a scenario temporal profile.

    Values are severity-scaled and clipped to the shared [0, 1] contract. Time
    is explicitly scaled/shifted and provenance must be recorded by the caller.
    """
    if severity_scale < 0:
        raise ValueError("severity_scale must be non-negative")
    if time_scale <= 0:
        raise ValueError("time_scale must be positive")
    if evidence_status not in {"observed", "proxy", "modeled", "extrapolated"}:
        raise ValueError("invalid evidence_status")

    result: list[ScenarioState] = []
    for index, point in enumerate(profile.points):
        domains = {
            name: DomainValue(
                value=max(0.0, min(1.0, value.value * severity_scale)),
                uncertainty=value.uncertainty,
                evidence_status=evidence_status,
            )
            for name, value in point.domains.items()
        }
        result.append(
            ScenarioState(
                state=f"empirical_t{index}",
                relative_time=max(0.0, point.relative_time * time_scale + time_offset),
                domains=domains,
            )
        )
    if len(result) < 2:
        raise ValueError("empirical trajectory requires at least two time points")
    return tuple(result)
