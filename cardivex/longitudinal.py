from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence

from .ingest import IngestRecord
from .features import CardiacState


@dataclass(frozen=True)
class LongitudinalGroup:
    """Observations belonging to one experimental unit across time."""

    group_id: str
    condition: str
    records: tuple[IngestRecord, ...]

    @property
    def times(self) -> tuple[float, ...]:
        return tuple(record.time for record in self.records)

    @property
    def dataset_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record.dataset_id for record in self.records}))

    def modalities_by_time(self) -> dict[float, tuple[str, ...]]:
        return {record.time: record.available_modalities for record in self.records}


@dataclass(frozen=True)
class LongitudinalValidation:
    group_id: str
    point_count: int
    missing_time_points: tuple[float, ...]
    duplicate_times: tuple[float, ...]
    modality_consistency: float
    valid: bool


def _group_key(record: IngestRecord, group_field: str) -> str:
    value = record.state.metadata.get(group_field)
    if value is None or not str(value).strip():
        raise ValueError(f"record {record.observation_id} lacks required grouping metadata: {group_field}")
    return str(value)


def group_longitudinal_records(
    records: Iterable[IngestRecord],
    *,
    group_field: str = "experimental_unit_id",
) -> tuple[LongitudinalGroup, ...]:
    """Group processed observations by an experimental-unit identifier."""
    buckets: dict[tuple[str, str], list[IngestRecord]] = {}
    for record in records:
        key = (_group_key(record, group_field), record.condition)
        buckets.setdefault(key, []).append(record)

    groups: list[LongitudinalGroup] = []
    for (group_id, condition), rows in sorted(buckets.items()):
        ordered = tuple(sorted(rows, key=lambda row: (row.time, row.observation_id)))
        groups.append(LongitudinalGroup(group_id, condition, ordered))
    return tuple(groups)


def validate_longitudinal_group(
    group: LongitudinalGroup,
    *,
    expected_times: Sequence[float] | None = None,
    required_modalities: Sequence[str] = (),
) -> LongitudinalValidation:
    """Check temporal uniqueness, expected coverage, and modality availability."""
    times = list(group.times)
    duplicates = tuple(sorted({time for time in times if times.count(time) > 1}))
    missing: tuple[float, ...] = ()
    if expected_times is not None:
        observed = set(times)
        missing = tuple(sorted(float(time) for time in expected_times if float(time) not in observed))

    modality_scores: list[float] = []
    required = set(required_modalities)
    for record in group.records:
        available = set(record.available_modalities)
        if required:
            modality_scores.append(len(available & required) / len(required))
        else:
            modality_scores.append(1.0)

    consistency = sum(modality_scores) / len(modality_scores) if modality_scores else 0.0
    valid = bool(group.records) and not duplicates and not missing and consistency == 1.0
    return LongitudinalValidation(
        group_id=group.group_id,
        point_count=len(group.records),
        missing_time_points=missing,
        duplicate_times=duplicates,
        modality_consistency=consistency,
        valid=valid,
    )


def align_to_time_grid(
    records: Sequence[IngestRecord],
    *,
    target_times: Sequence[float],
    tolerance: float = 0.0,
) -> dict[float, IngestRecord]:
    """Match observations to a target time grid without silently duplicating records."""
    if tolerance < 0 or not all(isfinite(float(t)) for t in target_times):
        raise ValueError("target times and tolerance must be finite/non-negative")
    ordered = sorted(records, key=lambda record: (record.time, record.observation_id))
    result: dict[float, IngestRecord] = {}
    used: set[str] = set()
    for target in target_times:
        candidates = [
            record for record in ordered
            if record.observation_id not in used and abs(float(record.time) - float(target)) <= tolerance
        ]
        if not candidates:
            continue
        selected = min(candidates, key=lambda record: (abs(record.time - target), record.observation_id))
        result[float(target)] = selected
        used.add(selected.observation_id)
    return result


def longitudinal_domain_series(group: LongitudinalGroup) -> dict[str, tuple[tuple[float, float], ...]]:
    """Return observed domain trajectories without interpolation."""
    domains = sorted(set().union(*(record.state.domain_scores.keys() for record in group.records)))
    return {
        domain: tuple(
            (record.time, float(record.state.domain_scores.get(domain, 0.0)))
            for record in group.records
        )
        for domain in domains
    }


def longitudinal_feature_series(group: LongitudinalGroup) -> dict[str, Mapping[float, Mapping[str, float]]]:
    """Return available multimodal feature vectors indexed by time."""
    output: dict[str, dict[float, Mapping[str, float]]] = {"imaging": {}, "functional": {}, "omics": {}}
    for record in group.records:
        state: CardiacState = record.state
        for name in output:
            modality = getattr(state, name)
            if modality is not None:
                output[name][record.time] = dict(modality.values)
    return output
