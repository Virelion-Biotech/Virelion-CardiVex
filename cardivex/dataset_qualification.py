from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .ingest import IngestRecord
from .longitudinal import LongitudinalGroup, validate_longitudinal_group


@dataclass(frozen=True)
class DatasetQualification:
    dataset_id: str
    record_count: int
    group_count: int
    condition_count: int
    modality_coverage: dict[str, float]
    longitudinal_coverage: float
    issues: tuple[str, ...]
    recommended_uses: tuple[str, ...]

    @property
    def usable(self) -> bool:
        return not self.issues and self.record_count > 0


def qualify_records(
    records: Sequence[IngestRecord],
    *,
    required_modalities: Sequence[str] = (),
    expected_times: Sequence[float] | None = None,
) -> DatasetQualification:
    if not records:
        raise ValueError("at least one processed record is required")
    dataset_ids = {record.dataset_id for record in records}
    if len(dataset_ids) != 1:
        raise ValueError("qualification requires records from exactly one dataset")
    dataset_id = next(iter(dataset_ids))
    modalities = {name: sum(name in record.available_modalities for record in records) / len(records) for name in ("imaging", "functional", "omics")}
    issues: list[str] = []
    for modality in required_modalities:
        if modalities.get(modality, 0.0) < 1.0:
            issues.append(f"MISSING_REQUIRED_MODALITY:{modality}")
    conditions = {record.condition for record in records}
    groups: tuple[LongitudinalGroup, ...] = ()
    try:
        from .longitudinal import group_longitudinal_records
        groups = group_longitudinal_records(records)
    except ValueError:
        issues.append("MISSING_EXPERIMENTAL_UNIT_IDS")
    validations = [validate_longitudinal_group(group, expected_times=expected_times, required_modalities=required_modalities) for group in groups]
    valid_groups = sum(item.valid for item in validations)
    longitudinal_coverage = valid_groups / len(validations) if validations else 0.0
    if groups and longitudinal_coverage < 1.0:
        issues.append("INCOMPLETE_LONGITUDINAL_GROUPS")
    uses: list[str] = ["domain_profile"]
    if longitudinal_coverage == 1.0 and len(groups) >= 2:
        uses.append("longitudinal_surrogate_validation")
    if all(modalities.get(name, 0.0) > 0 for name in ("imaging", "functional", "omics")):
        uses.append("multimodal_calibration")
    return DatasetQualification(
        dataset_id=dataset_id,
        record_count=len(records),
        group_count=len(groups),
        condition_count=len(conditions),
        modality_coverage=modalities,
        longitudinal_coverage=longitudinal_coverage,
        issues=tuple(sorted(set(issues))),
        recommended_uses=tuple(sorted(uses)),
    )
