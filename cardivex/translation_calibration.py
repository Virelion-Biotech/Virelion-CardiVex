from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Mapping, Sequence

from .ingest import IngestRecord
from .translation import TranslationProfile


@dataclass(frozen=True)
class TranslationCalibrationResult:
    profile: TranslationProfile
    sample_count: int
    modality_feature_counts: Mapping[str, int]
    source_dataset_ids: tuple[str, ...]


def _positive_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or not x:
        return 0.0
    mx = sum(x) / len(x)
    my = sum(y) / len(y)
    vx = sum((value - mx) ** 2 for value in x)
    vy = sum((value - my) ** 2 for value in y)
    denominator = sqrt(vx * vy)
    if denominator <= 1e-12:
        return 0.0
    correlation = sum((a - mx) * (b - my) for a, b in zip(x, y)) / denominator
    return max(0.0, min(1.0, correlation))


def _calibrate_modality(
    records: Sequence[IngestRecord],
    modality: str,
) -> tuple[dict[str, dict[str, float]], int]:
    selected = [record for record in records if getattr(record.state, modality) is not None]
    if not selected:
        return {}, 0
    domain_names = sorted(set().union(*(record.state.domain_scores.keys() for record in selected)))
    feature_names = sorted(set().union(*(getattr(record.state, modality).values.keys() for record in selected)))
    rules: dict[str, dict[str, float]] = {}
    for feature in feature_names:
        feature_values = [float(getattr(record.state, modality).values.get(feature, 0.0)) for record in selected]
        associations = {
            domain: _positive_correlation(
                [float(record.state.domain_scores.get(domain, 0.0)) for record in selected],
                feature_values,
            )
            for domain in domain_names
        }
        positive = {domain: score for domain, score in associations.items() if score > 0}
        total = sum(positive.values())
        rules[feature] = {
            domain: score / total
            for domain, score in positive.items()
        } if total > 0 else {}
    return rules, len(selected)


def fit_translation_profile(
    records: Sequence[IngestRecord],
    *,
    min_samples: int = 4,
) -> TranslationCalibrationResult:
    """Calibrate transparent domain-to-modality mappings from matched observations.

    We use normalized positive associations rather than causal inference. The
    resulting profile is suitable for surrogate benchmarking and should still be
    validated prospectively before scientific claims are attached to it.
    """
    if len(records) < min_samples:
        raise ValueError(f"at least {min_samples} matched observations are required")
    imaging, imaging_n = _calibrate_modality(records, "imaging")
    functional, functional_n = _calibrate_modality(records, "functional")
    omics, omics_n = _calibrate_modality(records, "omics")
    if not any((imaging, functional, omics)):
        raise ValueError("at least one multimodal measurement is required")
    profile = TranslationProfile(
        imaging=imaging,
        functional=functional,
        omics=omics,
    )
    return TranslationCalibrationResult(
        profile=profile,
        sample_count=len(records),
        modality_feature_counts={
            "imaging": imaging_n,
            "functional": functional_n,
            "omics": omics_n,
        },
        source_dataset_ids=tuple(sorted({record.dataset_id for record in records})),
    )
