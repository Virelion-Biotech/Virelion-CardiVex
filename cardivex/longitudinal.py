from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence

from .ingest import IngestRecord
from .features import CardiacState, ModalityVector


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


def validate_disjoint_longitudinal_groups(
    development: Sequence[LongitudinalGroup],
    held_out: Sequence[LongitudinalGroup],
) -> tuple[str, ...]:
    """Return experimental-unit IDs appearing in both development and held-out groups."""
    development_ids = {group.group_id for group in development}
    held_out_ids = {group.group_id for group in held_out}
    return tuple(sorted(development_ids & held_out_ids))


def collapse_subject_replicates(
    records: Sequence[IngestRecord],
    *,
    group_field: str = "experimental_unit_id",
) -> tuple[IngestRecord, ...]:
    """Collapse repeated observations from one biological unit at the same time.

    Domain and modality features are averaged, while provenance retains the
    contributing observation IDs. This prevents technical/biological repeats
    from receiving disproportionate weight in empirical calibration.
    """
    buckets: dict[tuple[str, str, float], list[IngestRecord]] = {}
    for record in records:
        group_id = _group_key(record, group_field)
        buckets.setdefault((group_id, record.condition, float(record.time)), []).append(record)

    collapsed: list[IngestRecord] = []
    for (group_id, condition, time), rows in sorted(buckets.items()):
        if len(rows) == 1:
            collapsed.append(rows[0])
            continue
        domain_names = sorted(set().union(*(row.state.domain_scores.keys() for row in rows)))
        domain_scores = {
            name: sum(float(row.state.domain_scores.get(name, 0.0)) for row in rows) / len(rows)
            for name in domain_names
        }
        modality_vectors: dict[str, ModalityVector] = {}
        for modality_name in ("imaging", "functional", "omics"):
            modalities = [getattr(row.state, modality_name) for row in rows]
            present = [modality for modality in modalities if modality is not None]
            if not present:
                continue
            keys = sorted(set().union(*(modality.values.keys() for modality in present)))
            modality_vectors[modality_name] = ModalityVector(
                name=modality_name,
                values={
                    key: sum(float(modality.values.get(key, 0.0)) for modality in present) / len(present)
                    for key in keys
                },
            )
        metadata = dict(rows[0].state.metadata)
        metadata.update(
            {
                "collapsed_replicates": str(len(rows)),
                "replicate_observation_ids": ",".join(sorted(row.observation_id for row in rows)),
                group_field: group_id,
            }
        )
        state = CardiacState(
            imaging=modality_vectors.get("imaging"),
            functional=modality_vectors.get("functional"),
            omics=modality_vectors.get("omics"),
            domain_scores=domain_scores,
            time=time,
            metadata=metadata,
        )
        available = tuple(
            name for name in ("imaging", "functional", "omics") if name in modality_vectors
        )
        collapsed.append(
            IngestRecord(
                observation_id=f"{group_id}:{condition}:{time:g}",
                dataset_id=rows[0].dataset_id,
                condition=condition,
                time=time,
                state=state,
                available_modalities=available,
                source_ref=";".join(sorted(row.source_ref for row in rows if row.source_ref)),
            )
        )
    return tuple(collapsed)


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
