from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence

from .correlation import domain_correlation_matrix
from .data_plan import DatasetAnalysisPlan
from .ingest import IngestRecord
from .longitudinal import group_longitudinal_records
from .phenotypes import EmpiricalPhenotypeProfile, fit_empirical_profile
from .temporal import EmpiricalTemporalProfile, fit_temporal_profile
from .translation import TranslationProfile
from .translation_calibration import TranslationCalibrationResult, fit_translation_profile


@dataclass(frozen=True)
class ConditionCalibration:
    condition: str
    profile: EmpiricalPhenotypeProfile
    correlation: Mapping[str, Mapping[str, float]]
    temporal: EmpiricalTemporalProfile | None


@dataclass(frozen=True)
class CalibrationArtifact:
    """Frozen development-only calibration state for downstream validation."""

    dataset_id: str
    condition_calibrations: tuple[ConditionCalibration, ...]
    translation: TranslationCalibrationResult | None
    development_record_ids: tuple[str, ...]
    held_out_group_ids: tuple[str, ...]
    excluded_record_ids: tuple[str, ...]
    source_dataset_ids: tuple[str, ...]
    artifact_id: str

    @property
    def translation_profile(self) -> TranslationProfile | None:
        return self.translation.profile if self.translation is not None else None

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "condition_calibrations": [
                {
                    "condition": item.condition,
                    "profile": asdict(item.profile),
                    "correlation": {
                        str(domain): dict(values)
                        for domain, values in item.correlation.items()
                    },
                    "temporal": asdict(item.temporal) if item.temporal else None,
                }
                for item in self.condition_calibrations
            ],
            "translation": asdict(self.translation) if self.translation else None,
            "development_record_ids": self.development_record_ids,
            "held_out_group_ids": self.held_out_group_ids,
            "excluded_record_ids": self.excluded_record_ids,
            "source_dataset_ids": self.source_dataset_ids,
            "artifact_id": self.artifact_id,
        }


def _artifact_id(
    dataset_id: str,
    development_record_ids: Sequence[str],
    held_out_group_ids: Sequence[str],
    conditions: Sequence[str],
) -> str:
    payload = {
        "dataset_id": dataset_id,
        "development_record_ids": sorted(development_record_ids),
        "held_out_group_ids": sorted(held_out_group_ids),
        "conditions": sorted(conditions),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()[:16]


def build_development_calibration(
    records: Sequence[IngestRecord],
    plan: DatasetAnalysisPlan,
    *,
    conditions: Sequence[str] | None = None,
    min_translation_samples: int = 4,
    normalize_time: bool = True,
) -> CalibrationArtifact:
    """Fit every calibration component using development records only.

    Candidate held-out groups from the analysis plan are removed before any
    empirical profile, correlation, temporal, or translation calibration is fit.
    """
    if not records:
        raise ValueError("at least one record is required")
    dataset_ids = {record.dataset_id for record in records}
    if dataset_ids != {plan.dataset_id}:
        raise ValueError("records do not match the analysis plan dataset")

    candidate_holdouts = set(plan.held_out_candidate_group_ids)
    groups = {group.group_id: group for group in group_longitudinal_records(records)}
    missing_groups = candidate_holdouts - set(groups)
    if missing_groups:
        raise ValueError("analysis plan references unknown holdout groups: " + ", ".join(sorted(missing_groups)))

    excluded_ids = {
        record.observation_id
        for group_id, group in groups.items()
        if group_id in candidate_holdouts
        for record in group.records
    }
    development = tuple(sorted(
        (record for record in records if record.observation_id not in excluded_ids),
        key=lambda record: record.observation_id,
    ))
    if not development:
        raise ValueError("no development records remain after holdout exclusion")

    selected_conditions = tuple(sorted(set(conditions or (record.condition for record in development))))
    calibrations: list[ConditionCalibration] = []
    for condition in selected_conditions:
        condition_records = [record for record in development if record.condition == condition]
        if not condition_records:
            raise ValueError(f"condition has no development records: {condition}")
        profile = fit_empirical_profile(condition_records, condition=condition)
        correlation = domain_correlation_matrix(condition_records, condition=condition)
        temporal = None
        unique_times = {float(record.time) for record in condition_records}
        if len(unique_times) >= 2:
            temporal = fit_temporal_profile(
                condition_records,
                condition=condition,
                normalize_time=normalize_time,
            )
        calibrations.append(
            ConditionCalibration(
                condition=condition,
                profile=profile,
                correlation=correlation,
                temporal=temporal,
            )
        )

    multimodal_records = [
        record for record in development
        if all(name in record.available_modalities for name in ("imaging", "functional", "omics"))
    ]
    translation = None
    if len(multimodal_records) >= min_translation_samples:
        translation = fit_translation_profile(
            multimodal_records,
            min_samples=min_translation_samples,
        )

    development_ids = tuple(record.observation_id for record in development)
    artifact_id = _artifact_id(
        plan.dataset_id,
        development_ids,
        tuple(sorted(candidate_holdouts)),
        selected_conditions,
    )
    return CalibrationArtifact(
        dataset_id=plan.dataset_id,
        condition_calibrations=tuple(calibrations),
        translation=translation,
        development_record_ids=development_ids,
        held_out_group_ids=tuple(sorted(candidate_holdouts)),
        excluded_record_ids=tuple(sorted(excluded_ids)),
        source_dataset_ids=(plan.dataset_id,),
        artifact_id=artifact_id,
    )


def calibration_json(artifact: CalibrationArtifact) -> str:
    return json.dumps(artifact.to_dict(), sort_keys=True, indent=2)
