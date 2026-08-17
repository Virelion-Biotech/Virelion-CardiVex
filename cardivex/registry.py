from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping


@dataclass(frozen=True)
class EvidenceRecord:
    """Structured provenance for one measured or derived evidence item."""

    evidence_id: str
    source_type: str
    source_ref: str
    description: str
    modality: str | None = None
    population: str | None = None
    timepoint: str | None = None
    quality_score: float = 1.0
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id cannot be empty")
        if not self.source_type.strip():
            raise ValueError("source_type cannot be empty")
        if not self.source_ref.strip():
            raise ValueError("source_ref cannot be empty")
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("quality_score must be in [0, 1]")


@dataclass(frozen=True)
class DatasetRecord:
    """Metadata contract for a dataset feeding the phenotype pipeline."""

    dataset_id: str
    name: str
    species: str
    model: str
    assay_types: tuple[str, ...]
    condition_labels: tuple[str, ...]
    source_ref: str
    version: str = "1.0.0"
    sample_count: int | None = None
    processed_feature_contract: str = "cardivex-v1"
    evidence_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.dataset_id.startswith("DS-"):
            raise ValueError("dataset_id must start with DS-")
        if not self.name.strip():
            raise ValueError("dataset name cannot be empty")
        if self.sample_count is not None and self.sample_count < 0:
            raise ValueError("sample_count cannot be negative")


class EvidenceRegistry:
    """Deterministic in-memory registry for evidence and dataset metadata."""

    def __init__(self, records: Iterable[EvidenceRecord] = ()) -> None:
        self._records: dict[str, EvidenceRecord] = {}
        for record in records:
            self.add(record)

    def add(self, record: EvidenceRecord) -> None:
        if record.evidence_id in self._records:
            raise ValueError(f"duplicate evidence_id: {record.evidence_id}")
        self._records[record.evidence_id] = record

    def get(self, evidence_id: str) -> EvidenceRecord:
        try:
            return self._records[evidence_id]
        except KeyError as exc:
            raise KeyError(f"unknown evidence_id: {evidence_id}") from exc

    def all(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))


class DatasetRegistry:
    def __init__(self, records: Iterable[DatasetRecord] = ()) -> None:
        self._records: dict[str, DatasetRecord] = {}
        for record in records:
            self.add(record)

    def add(self, record: DatasetRecord) -> None:
        if record.dataset_id in self._records:
            raise ValueError(f"duplicate dataset_id: {record.dataset_id}")
        self._records[record.dataset_id] = record

    def get(self, dataset_id: str) -> DatasetRecord:
        try:
            return self._records[dataset_id]
        except KeyError as exc:
            raise KeyError(f"unknown dataset_id: {dataset_id}") from exc

    def by_condition(self, condition: str) -> tuple[DatasetRecord, ...]:
        return tuple(
            record for record in self.all() if condition in record.condition_labels
        )

    def all(self) -> tuple[DatasetRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))
