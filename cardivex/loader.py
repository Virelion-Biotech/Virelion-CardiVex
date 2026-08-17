from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .ingest import IngestRecord, ingest_processed_observation


REQUIRED_COLUMNS = {"observation_id", "dataset_id", "condition", "time"}


def _parse_mapping(value: str | Mapping[str, float] | None) -> dict[str, float] | None:
    if value is None or value == "":
        return None
    if isinstance(value, Mapping):
        return {str(k): float(v) for k, v in value.items()}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("feature mapping must decode to an object")
    return {str(k): float(v) for k, v in parsed.items()}


def records_from_rows(rows: Iterable[Mapping[str, Any]]) -> list[IngestRecord]:
    records: list[IngestRecord] = []
    for row in rows:
        missing = REQUIRED_COLUMNS - set(row)
        if missing:
            raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")
        domain_scores = _parse_mapping(row.get("domain_scores")) or {}
        record = ingest_processed_observation(
            observation_id=str(row["observation_id"]),
            dataset_id=str(row["dataset_id"]),
            condition=str(row["condition"]),
            time=float(row["time"]),
            domain_scores=domain_scores,
            imaging=_parse_mapping(row.get("imaging")),
            functional=_parse_mapping(row.get("functional")),
            omics=_parse_mapping(row.get("omics")),
            source_ref=str(row.get("source_ref", "")),
        )
        records.append(record)
    return records


def load_csv(path: str | Path) -> list[IngestRecord]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", newline="", encoding="utf-8") as handle:
        return records_from_rows(csv.DictReader(handle))
