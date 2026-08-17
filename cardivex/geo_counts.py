from __future__ import annotations

from dataclasses import dataclass
import csv
import gzip
from math import log1p, sqrt
from pathlib import Path
from typing import Mapping, Sequence

from .features import CardiacState, ModalityVector
from .ingest import IngestRecord
from .geo_metadata import GEOSampleMetadata, parse_gse144424_sample_title


@dataclass(frozen=True)
class GEOCountMatrix:
    gene_ids: tuple[str, ...]
    sample_ids: tuple[str, ...]
    counts: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class ModuleScoreConfig:
    """Map CardiVex phenotype domains to externally curated gene modules."""

    domain_gene_sets: Mapping[str, tuple[str, ...]]
    minimum_genes: int = 2


def _open_text(path: str | Path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("rt", encoding="utf-8", newline="")


def read_geo_counts(path: str | Path) -> GEOCountMatrix:
    """Read a tab-delimited GEO count matrix with genes in rows and samples in columns."""
    with _open_text(path) as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader, None)
        if not header or len(header) < 2:
            raise ValueError("count matrix must contain a gene column and at least one sample")
        sample_ids = tuple(cell.strip() for cell in header[1:])
        genes: list[str] = []
        rows: list[tuple[float, ...]] = []
        width = len(sample_ids)
        for line in reader:
            if not line:
                continue
            gene_id = line[0].strip()
            if not gene_id:
                continue
            values = tuple(float(value) for value in line[1:])
            if len(values) != width:
                raise ValueError(f"row width mismatch for gene {gene_id}")
            if any(value < 0 for value in values):
                raise ValueError(f"negative count encountered for gene {gene_id}")
            genes.append(gene_id)
            rows.append(values)
    if not genes:
        raise ValueError("count matrix contains no genes")
    if len(set(sample_ids)) != len(sample_ids):
        raise ValueError("sample IDs must be unique")
    return GEOCountMatrix(tuple(genes), sample_ids, tuple(rows))


def _sample_totals(matrix: GEOCountMatrix) -> tuple[float, ...]:
    return tuple(sum(row[index] for row in matrix.counts) for index in range(len(matrix.sample_ids)))


def _log_cpm(matrix: GEOCountMatrix) -> tuple[dict[str, float], ...]:
    totals = _sample_totals(matrix)
    result: list[dict[str, float]] = [dict() for _ in matrix.sample_ids]
    for gene, row in zip(matrix.gene_ids, matrix.counts):
        for index, value in enumerate(row):
            scale = totals[index]
            cpm = 0.0 if scale <= 0 else value / scale * 1_000_000.0
            result[index][gene] = log1p(cpm)
    return tuple(result)


def _module_score(expression: Mapping[str, float], genes: Sequence[str], minimum_genes: int) -> float:
    observed = [expression[gene] for gene in genes if gene in expression]
    if len(observed) < minimum_genes:
        raise ValueError("gene module has insufficient overlap with the count matrix")
    return sum(observed) / len(observed)


def score_count_modules(
    matrix: GEOCountMatrix,
    metadata: Sequence[GEOSampleMetadata],
    config: ModuleScoreConfig,
) -> tuple[IngestRecord, ...]:
    """Convert processed GEO counts into descriptive downstream phenotype scores.

    This adapter intentionally does not infer causality. RNA-derived scores are
    represented as the omics modality only; imaging and functional measurements
    remain absent rather than being fabricated as empty vectors.
    """
    if tuple(item.sample_id for item in metadata) != matrix.sample_ids:
        raise ValueError("metadata sample IDs must match count-matrix columns exactly")
    if not config.domain_gene_sets:
        raise ValueError("at least one domain gene set is required")
    expression = _log_cpm(matrix)
    raw: list[dict[str, float]] = []
    for sample in expression:
        raw.append({domain: _module_score(sample, genes, config.minimum_genes) for domain, genes in config.domain_gene_sets.items()})

    # Cohort-relative z-normalization followed by [0,1] scaling keeps downstream
    # phenotype contracts comparable without asserting an absolute biological scale.
    domains = tuple(sorted(config.domain_gene_sets))
    centers = {domain: sum(row[domain] for row in raw) / len(raw) for domain in domains}
    scales: dict[str, float] = {}
    for domain in domains:
        variance = sum((row[domain] - centers[domain]) ** 2 for row in raw) / max(1, len(raw) - 1)
        scales[domain] = sqrt(variance) or 1.0

    records: list[IngestRecord] = []
    for index, meta in enumerate(metadata):
        scores = {
            domain: max(0.0, min(1.0, 0.5 + 0.15 * (raw[index][domain] - centers[domain]) / scales[domain]))
            for domain in domains
        }
        state = CardiacState(
            domain_scores=scores,
            omics=ModalityVector(
                name="omics",
                values={"rna_module_features": float(len(domains))},
            ),
            time=meta.elapsed_hours,
            metadata={
                "subject_id": meta.subject_id,
                "sample_id": meta.sample_id,
                "condition_code": meta.condition_code,
                "dataset_id": "GSE144424",
            },
        )
        records.append(
            IngestRecord(
                observation_id=meta.sample_id,
                dataset_id="GSE144424",
                condition=meta.condition,
                time=meta.elapsed_hours,
                state=state,
                available_modalities=("omics",),
                source_ref=f"GEO:GSE144424:{meta.sample_id}",
            )
        )
    return tuple(records)


def parse_gse144424_metadata(sample_titles: Mapping[str, str]) -> tuple[GEOSampleMetadata, ...]:
    return tuple(
        parse_gse144424_sample_title(sample_id, title)
        for sample_id, title in sorted(sample_titles.items())
    )
