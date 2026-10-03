from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .features import CardiacState
from .ingest import IngestRecord
from .registry import DatasetRegistry


@dataclass(frozen=True)
class DatasetBatch:
    dataset_id: str
    records: tuple[IngestRecord, ...]

    @property
    def observations(self) -> tuple[CardiacState, ...]:
        return tuple(record.state for record in self.records)

    @property
    def conditions(self) -> tuple[str, ...]:
        return tuple(record.condition for record in self.records)

    def by_condition(self, condition: str) -> "DatasetBatch":
        return DatasetBatch(
            dataset_id=self.dataset_id,
            records=tuple(r for r in self.records if r.condition == condition),
        )

    def require_nonempty(self) -> "DatasetBatch":
        if not self.records:
            raise ValueError(f"dataset batch {self.dataset_id} is empty")
        return self


def assemble_batch(
    dataset_id: str,
    records: Iterable[IngestRecord],
    registry: DatasetRegistry | None = None,
) -> DatasetBatch:
    items = tuple(record for record in records if record.dataset_id == dataset_id)
    if registry is not None:
        registry.get(dataset_id)
    if not items:
        raise ValueError(f"no observations found for dataset_id: {dataset_id}")
    return DatasetBatch(dataset_id=dataset_id, records=items)


def split_by_condition(batch: DatasetBatch, conditions: Sequence[str]) -> dict[str, DatasetBatch]:
    requested = tuple(dict.fromkeys(conditions))
    return {condition: batch.by_condition(condition) for condition in requested}
