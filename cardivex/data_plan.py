from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .dataset_qualification import DatasetQualification, qualify_records
from .ingest import IngestRecord
from .longitudinal import group_longitudinal_records


@dataclass(frozen=True)
class DatasetAnalysisPlan:
    """Deterministic plan describing how one dataset may enter CardiVex."""

    dataset_id: str
    profile_record_ids: tuple[str, ...]
    longitudinal_group_ids: tuple[str, ...]
    multimodal_record_ids: tuple[str, ...]
    held_out_candidate_group_ids: tuple[str, ...]
    condition_counts: Mapping[str, int]
    qualification: DatasetQualification

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "profile_record_ids": self.profile_record_ids,
            "longitudinal_group_ids": self.longitudinal_group_ids,
            "multimodal_record_ids": self.multimodal_record_ids,
            "held_out_candidate_group_ids": self.held_out_candidate_group_ids,
            "condition_counts": dict(self.condition_counts),
            "qualification": {
                "record_count": self.qualification.record_count,
                "group_count": self.qualification.group_count,
                "condition_count": self.qualification.condition_count,
                "modality_coverage": dict(self.qualification.modality_coverage),
                "longitudinal_coverage": self.qualification.longitudinal_coverage,
                "issues": self.qualification.issues,
                "recommended_uses": self.qualification.recommended_uses,
            },
        }


def build_analysis_plan(
    records: Sequence[IngestRecord],
    *,
    required_modalities: Sequence[str] = (),
    expected_times: Sequence[float] | None = None,
    min_holdout_groups: int = 1,
) -> DatasetAnalysisPlan:
    """Build a deterministic downstream plan after dataset qualification."""
    if min_holdout_groups < 1:
        raise ValueError("min_holdout_groups must be positive")
    qualification = qualify_records(
        records,
        required_modalities=required_modalities,
        expected_times=expected_times,
    )
    if not qualification.usable:
        raise ValueError("dataset is not qualified: " + ", ".join(qualification.issues))

    ordered_records = tuple(sorted(records, key=lambda record: record.observation_id))
    groups = tuple(sorted(group_longitudinal_records(ordered_records), key=lambda group: group.group_id))
    multimodal = tuple(
        record.observation_id
        for record in ordered_records
        if all(name in record.available_modalities for name in ("imaging", "functional", "omics"))
    )
    condition_counts: dict[str, int] = {}
    for record in ordered_records:
        condition_counts[record.condition] = condition_counts.get(record.condition, 0) + 1

    holdout = tuple(group.group_id for group in groups[-min_holdout_groups:]) if len(groups) >= min_holdout_groups else ()
    return DatasetAnalysisPlan(
        dataset_id=qualification.dataset_id,
        profile_record_ids=tuple(record.observation_id for record in ordered_records),
        longitudinal_group_ids=tuple(group.group_id for group in groups),
        multimodal_record_ids=multimodal,
        held_out_candidate_group_ids=holdout,
        condition_counts=dict(sorted(condition_counts.items())),
        qualification=qualification,
    )
