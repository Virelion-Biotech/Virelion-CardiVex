from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .features import CardiacState, ModalityVector
from .ingest import IngestRecord


@dataclass(frozen=True)
class PhysiologicalFeatureConfig:
    """Explicit normalization contract for one processed physiology measure."""

    source_name: str
    output_name: str
    lower: float
    upper: float
    inverse: bool = False

    def normalize(self, value: float) -> float:
        if self.lower >= self.upper:
            raise ValueError("feature lower bound must be less than upper bound")
        x = float(value)
        if x != x:
            raise ValueError(f"feature '{self.source_name}' is NaN")
        clipped = max(self.lower, min(self.upper, x))
        score = (clipped - self.lower) / (self.upper - self.lower)
        return 1.0 - score if self.inverse else score


@dataclass(frozen=True)
class GSE234907Observation:
    """Processed physiology measurements tied to one organoid/experimental unit."""

    observation_id: str
    experimental_unit: str
    condition: str
    time: float
    measurements: Mapping[str, float]
    source_ref: str


def normalize_physiology(
    measurements: Mapping[str, float],
    configs: Sequence[PhysiologicalFeatureConfig],
) -> dict[str, float]:
    if not configs:
        raise ValueError("at least one physiological feature config is required")
    normalized: dict[str, float] = {}
    for config in configs:
        if config.source_name not in measurements:
            continue
        normalized[config.output_name] = config.normalize(measurements[config.source_name])
    if not normalized:
        raise ValueError("none of the configured physiological features were present")
    return normalized


def ingest_gse234907_physiology(
    observations: Sequence[GSE234907Observation],
    configs: Sequence[PhysiologicalFeatureConfig],
    *,
    domain_scores: Mapping[str, float] | None = None,
) -> tuple[IngestRecord, ...]:
    """Convert externally processed GSE234907 sensor summaries to functional states.

    The adapter deliberately requires the physiological measurements as input;
    it never derives them from RNA-seq or invents missing sensor data.
    """
    records: list[IngestRecord] = []
    seen: set[str] = set()
    for observation in observations:
        if observation.observation_id in seen:
            raise ValueError(f"duplicate observation ID: {observation.observation_id}")
        if observation.time < 0:
            raise ValueError("time must be non-negative")
        seen.add(observation.observation_id)
        normalized = normalize_physiology(observation.measurements, configs)
        records.append(
            IngestRecord(
                observation_id=observation.observation_id,
                dataset_id="GSE234907",
                condition=observation.condition,
                time=observation.time,
                state=CardiacState(
                    functional=ModalityVector("functional", normalized),
                    domain_scores=dict(domain_scores or {}),
                    time=observation.time,
                    metadata={
                        "experimental_unit": observation.experimental_unit,
                        "source_ref": observation.source_ref,
                    },
                ),
                available_modalities=("functional",),
                source_ref=observation.source_ref,
            )
        )
    return tuple(records)
