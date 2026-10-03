from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .geo_counts import GEOCountMatrix, ModuleScoreConfig, ModuleScoreScaler, fit_module_scaler, score_count_modules
from .geo_metadata import GEOSampleMetadata
from .ingest import IngestRecord


@dataclass(frozen=True)
class RealDataSplit:
    development_sample_ids: tuple[str, ...]
    held_out_sample_ids: tuple[str, ...]


def build_subject_disjoint_split(
    metadata: Sequence[GEOSampleMetadata],
    *,
    held_out_subjects: Sequence[str],
) -> RealDataSplit:
    """Build a subject-disjoint split before any feature scaling or model fitting."""
    held = {str(subject) for subject in held_out_subjects}
    if not held:
        raise ValueError("at least one held-out subject is required")
    development = tuple(item.sample_id for item in metadata if item.subject_id not in held)
    held_out = tuple(item.sample_id for item in metadata if item.subject_id in held)
    if not development or not held_out:
        raise ValueError("split must contain both development and held-out samples")
    return RealDataSplit(tuple(sorted(development)), tuple(sorted(held_out)))


def score_subject_disjoint_dataset(
    matrix: GEOCountMatrix,
    metadata: Sequence[GEOSampleMetadata],
    config: ModuleScoreConfig,
    split: RealDataSplit,
) -> tuple[tuple[IngestRecord, ...], ModuleScoreScaler]:
    """Normalize on development samples only and transform all samples identically."""
    scaler = fit_module_scaler(
        matrix,
        config,
        fit_sample_ids=split.development_sample_ids,
    )
    records = score_count_modules(
        matrix,
        metadata,
        config,
        scaler=scaler,
    )
    return records, scaler


def collapse_replicates(records: Sequence[IngestRecord]) -> tuple[IngestRecord, ...]:
    """Collapse repeated samples within subject x condition x time without losing provenance."""
    buckets: dict[tuple[str, str, float], list[IngestRecord]] = {}
    for record in records:
        subject = record.state.metadata.get("experimental_unit_id") or record.state.metadata.get("subject_id")
        if not subject:
            raise ValueError(f"record {record.observation_id} lacks experimental-unit metadata")
        buckets.setdefault((str(subject), record.condition, float(record.time)), []).append(record)

    collapsed: list[IngestRecord] = []
    for (subject, condition, time), rows in sorted(buckets.items()):
        if len(rows) == 1:
            collapsed.append(rows[0])
            continue
        domains = sorted(set().union(*(row.state.domain_scores.keys() for row in rows)))
        scores = {
            domain: sum(float(row.state.domain_scores.get(domain, 0.0)) for row in rows) / len(rows)
            for domain in domains
        }
        first = rows[0]
        sample_ids = tuple(sorted(row.observation_id for row in rows))
        metadata_out = {
            **dict(first.state.metadata),
            "experimental_unit_id": subject,
            "collapsed_replicate_count": str(len(rows)),
            "collapsed_sample_ids": ",".join(sample_ids),
        }
        from .features import CardiacState
        state = CardiacState(
            domain_scores=scores,
            imaging=first.state.imaging,
            functional=first.state.functional,
            omics=first.state.omics,
            time=time,
            metadata=metadata_out,
        )
        collapsed.append(
            IngestRecord(
                observation_id=f"{subject}_{condition}_{int(time) if float(time).is_integer() else time:g}",
                dataset_id=first.dataset_id,
                condition=condition,
                time=time,
                state=state,
                available_modalities=first.available_modalities,
                source_ref=first.source_ref,
            )
        )
    return tuple(collapsed)
