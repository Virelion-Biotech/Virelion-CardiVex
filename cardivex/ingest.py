from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .adapters import imaging_features, functional_features, omics_features
from .features import CardiacState, ModalityVector


@dataclass(frozen=True)
class IngestRecord:
    """Processed observation mapped into the common cardiac-state contract."""

    observation_id: str
    dataset_id: str
    condition: str
    time: float
    state: CardiacState
    available_modalities: tuple[str, ...]
    source_ref: str = ""


def ingest_processed_observation(
    *,
    observation_id: str,
    dataset_id: str,
    condition: str,
    time: float,
    domain_scores: Mapping[str, float],
    imaging: Mapping[str, float] | None = None,
    functional: Mapping[str, float] | None = None,
    omics: Mapping[str, float] | None = None,
    source_ref: str = "",
) -> IngestRecord:
    """Create a CardiacState from already processed measurements.

    This boundary intentionally accepts processed values only. Acquisition,
    wet-lab procedures, and raw-data processing remain outside this package.
    """
    if not observation_id.strip():
        raise ValueError("observation_id cannot be empty")
    if not dataset_id.strip():
        raise ValueError("dataset_id cannot be empty")
    if not condition.strip():
        raise ValueError("condition cannot be empty")
    if time < 0:
        raise ValueError("time must be non-negative")

    modalities: list[ModalityVector] = []
    if imaging is not None:
        modalities.append(imaging_features(imaging))
    if functional is not None:
        modalities.append(functional_features(functional))
    if omics is not None:
        modalities.append(omics_features(omics))

    state = CardiacState(
        imaging=next((m for m in modalities if m.name == "imaging"), None),
        functional=next((m for m in modalities if m.name == "functional"), None),
        omics=next((m for m in modalities if m.name == "omics"), None),
        domain_scores=dict(domain_scores),
        time=time,
        metadata={
            "observation_id": observation_id,
            "dataset_id": dataset_id,
            "condition": condition,
            "source_ref": source_ref,
        },
    )
    return IngestRecord(
        observation_id=observation_id,
        dataset_id=dataset_id,
        condition=condition,
        time=time,
        state=state,
        available_modalities=tuple(m.name for m in modalities),
        source_ref=source_ref,
    )


def require_modalities(record: IngestRecord, required: Sequence[str]) -> None:
    """Validate that an observation contains the modalities a benchmark needs."""
    available = set(record.available_modalities)
    missing = [name for name in required if name not in available]
    if missing:
        raise ValueError(
            f"observation {record.observation_id} is missing required modalities: {', '.join(missing)}"
        )
