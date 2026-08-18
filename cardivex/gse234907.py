from __future__ import annotations

from dataclasses import dataclass
import csv
import gzip
from math import log1p
from pathlib import Path
from typing import Mapping, Sequence

from .features import CardiacState, ModalityVector
from .ingest import IngestRecord


@dataclass(frozen=True)
class GSE234907Matrix:
    sample_ids: tuple[str, ...]
    classes: tuple[str, ...]
    gene_ids: tuple[str, ...]
    counts: tuple[tuple[float, ...], ...]


def _open_text(path: str | Path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("rt", encoding="utf-8", newline="")


def read_gse234907_heart_counts(path: str | Path) -> GSE234907Matrix:
    """Read the GSE234907 Heart_counts.txt.gz supplementary matrix.

    The file uses two metadata rows (#KEY and #CLASS) and ends with a
    non-numeric annotation row after the count records; that row is ignored.
    """
    with _open_text(path) as handle:
        reader = csv.reader(handle, delimiter="\t")
        key_row = next(reader, None)
        class_row = next(reader, None)
        if not key_row or not class_row or key_row[0] != "#KEY" or class_row[0] != "#CLASS":
            raise ValueError("expected #KEY and #CLASS metadata rows")
        sample_ids = tuple(key_row[1:])
        classes = tuple(class_row[1:])
        if not sample_ids or len(sample_ids) != len(classes):
            raise ValueError("sample IDs and classes must have equal non-zero length")

        gene_ids: list[str] = []
        counts: list[tuple[float, ...]] = []
        for row in reader:
            if not row or row[0] in {"Geneid", ""}:
                continue
            if len(row) != len(sample_ids) + 1:
                raise ValueError(f"row width mismatch for {row[0]}")
            try:
                values = tuple(float(value) for value in row[1:])
            except ValueError:
                # Known trailing annotation row in the GEO supplementary file.
                continue
            if any(value < 0 for value in values):
                raise ValueError(f"negative count encountered for {row[0]}")
            gene_ids.append(row[0])
            counts.append(values)

    if len(set(sample_ids)) != len(sample_ids):
        raise ValueError("sample IDs must be unique")
    return GSE234907Matrix(sample_ids, classes, tuple(gene_ids), tuple(counts))


def _log_cpm(matrix: GSE234907Matrix) -> tuple[dict[str, float], ...]:
    totals = [sum(row[index] for row in matrix.counts) for index in range(len(matrix.sample_ids))]
    result = [dict() for _ in matrix.sample_ids]
    for gene, row in zip(matrix.gene_ids, matrix.counts):
        for index, value in enumerate(row):
            cpm = 0.0 if totals[index] <= 0 else value / totals[index] * 1_000_000.0
            result[index][gene] = log1p(cpm)
    return tuple(result)


def score_gse234907_modules(
    matrix: GSE234907Matrix,
    *,
    gene_sets: Mapping[str, Sequence[str]],
    minimum_genes: int = 3,
) -> tuple[IngestRecord, ...]:
    """Create descriptive RNA-derived CardiacState records from the 2D/3D matrix."""
    if not gene_sets:
        raise ValueError("at least one gene set is required")
    expression = _log_cpm(matrix)
    records: list[IngestRecord] = []
    for index, sample_id in enumerate(matrix.sample_ids):
        scores: dict[str, float] = {}
        for domain, genes in gene_sets.items():
            values = [expression[index][gene] for gene in genes if gene in expression[index]]
            if len(values) < minimum_genes:
                raise ValueError(f"gene set '{domain}' has insufficient overlap")
            scores[domain] = sum(values) / len(values)
        state = CardiacState(
            domain_scores=scores,
            omics=ModalityVector("omics", {"rna_module_features": float(len(scores))}),
            time=0.0,
            metadata={
                "experimental_unit_id": sample_id,
                "sample_id": sample_id,
                "gse234907_class": matrix.classes[index],
                "dataset_id": "GSE234907",
            },
        )
        records.append(
            IngestRecord(
                observation_id=sample_id,
                dataset_id="GSE234907",
                condition=matrix.classes[index],
                time=0.0,
                state=state,
                available_modalities=("omics",),
                source_ref=f"GEO:GSE234907:{sample_id}",
            )
        )
    return tuple(records)


def class_groups(records: Sequence[IngestRecord]) -> dict[str, tuple[str, ...]]:
    groups: dict[str, list[str]] = {}
    for record in records:
        groups.setdefault(record.condition, []).append(record.observation_id)
    return {condition: tuple(sorted(ids)) for condition, ids in sorted(groups.items())}
