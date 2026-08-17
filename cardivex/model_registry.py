from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ModelRecord:
    model_id: str
    name: str
    version: str
    feature_contract: str
    training_split: str
    training_sample_count: int | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id cannot be empty")
        if not self.name.strip():
            raise ValueError("model name cannot be empty")
        if not self.version.strip():
            raise ValueError("model version cannot be empty")
        if not self.feature_contract.strip():
            raise ValueError("feature_contract cannot be empty")
        if not self.training_split.strip():
            raise ValueError("training_split cannot be empty")
        if self.training_sample_count is not None and self.training_sample_count < 1:
            raise ValueError("training_sample_count must be positive when provided")


class ModelRegistry:
    """Deterministic registry for model metadata and benchmark lineage."""

    def __init__(self, records: Iterable[ModelRecord] = ()) -> None:
        self._records: dict[str, ModelRecord] = {}
        for record in records:
            self.add(record)

    def add(self, record: ModelRecord) -> None:
        if record.model_id in self._records:
            raise ValueError(f"duplicate model_id: {record.model_id}")
        self._records[record.model_id] = record

    def get(self, model_id: str) -> ModelRecord:
        try:
            return self._records[model_id]
        except KeyError as exc:
            raise KeyError(f"unknown model_id: {model_id}") from exc

    def all(self) -> tuple[ModelRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))
