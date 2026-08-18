from __future__ import annotations

from dataclasses import dataclass
import csv
import gzip
from math import log1p, sqrt
from pathlib import Path
from typing import Mapping, Sequence

from .features import CardiacState, ModalityVector
from .ingest import IngestRecord
from .geo_metadata import GEOSampleMetadata, parse_gse144424_count_column, parse_gse144424_sample_title


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


@dataclass(frozen=True)
class ModuleScoreScaler:
    """Development-only center/scale parameters for leakage-safe module scoring."""

    centers: Mapping[str, float]
    scales: Mapping[str, float]
    fit_sample_ids: tuple[str, ...]


def _open_text(path: str | Path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("rt", encoding="utf-8", newline="")


def read_geo_counts(path: str | Path, *, sample_start: int | None = None) -> GEOCountMatrix:
    """Read a GEO tab-delimited count matrix with optional annotation columns."""
    with _open_text(path) as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader, None)
        if not header or len(header) < 2:
            raise ValueError("count matrix must contain a gene column and at least one sample")

        if sample_start is None:
            sample_start = 6 if len(header) > 6 and header[5].strip().lower() == "length" else 1
        if sample_start < 1 or sample_start >= len(header):
            raise ValueError("sample_start must point to at least one sample column")

        sample_ids = tuple(cell.strip() for cell in header[sample_start:])
        genes: list[str] = []
        rows: list[tuple[float, ...]] = []
        width = len(sample_ids)
        for line in reader:
            if not line:
                continue
            gene_id = line[0].strip().split(".", 1)[0]
            if not gene_id:
                continue
            values = tuple(float(value) for value in line[sample_start:])
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


def _raw_module_scores(
    matrix: GEOCountMatrix,
    config: ModuleScoreConfig,
) -> list[dict[str, float]]:
    expression = _log_cpm(matrix)
    return [
        {
            domain: _module_score(sample, genes, config.minimum_genes)
            for domain, genes in config.domain_gene_sets.items()
        }
        for sample in expression
    ]


def fit_module_scaler(
    matrix: GEOCountMatrix,
    config: ModuleScoreConfig,
    *,
    fit_sample_ids: Sequence[str],
) -> ModuleScoreScaler:
    """Fit module normalization on development samples only."""
    fit_ids = tuple(sorted(set(fit_sample_ids)))
    positions = {sample_id: index for index, sample_id in enumerate(matrix.sample_ids)}
    missing = [sample_id for sample_id in fit_ids if sample_id not in positions]
    if missing:
        raise ValueError("unknown fit sample IDs: " + ", ".join(missing))
    if not fit_ids:
        raise ValueError("at least one fit sample is required")

    raw = _raw_module_scores(matrix, config)
    domains = tuple(sorted(config.domain_gene_sets))
    fit_rows = [raw[positions[sample_id]] for sample_id in fit_ids]
    centers = {domain: sum(row[domain] for row in fit_rows) / len(fit_rows) for domain in domains}
    scales: dict[str, float] = {}
    for domain in domains:
        variance = sum((row[domain] - centers[domain]) ** 2 for row in fit_rows) / max(1, len(fit_rows) - 1)
        scales[domain] = sqrt(variance) or 1.0
    return ModuleScoreScaler(centers=centers, scales=scales, fit_sample_ids=fit_ids)


def score_count_modules(
    matrix: GEOCountMatrix,
    metadata: Sequence[GEOSampleMetadata],
    config: ModuleScoreConfig,
    *,
    scaler: ModuleScoreScaler | None = None,
    fit_sample_ids: Sequence[str] | None = None,
) -> tuple[IngestRecord, ...]:
    """Convert processed GEO counts into leakage-aware descriptive phenotype scores."""
    if tuple(item.sample_id for item in metadata) != matrix.sample_ids:
        raise ValueError("metadata sample IDs must match count-matrix columns exactly")
    if not config.domain_gene_sets:
        raise ValueError("at least one domain gene set is required")
    if scaler is not None and fit_sample_ids is not None:
        raise ValueError("provide scaler or fit_sample_ids, not both")
    if scaler is None:
        scaler = fit_module_scaler(
            matrix,
            config,
            fit_sample_ids=fit_sample_ids or matrix.sample_ids,
        )

    raw = _raw_module_scores(matrix, config)
    domains = tuple(sorted(config.domain_gene_sets))
    scores_by_sample = [
        {
            domain: max(
                0.0,
                min(1.0, 0.5 + 0.15 * (row[domain] - scaler.centers[domain]) / scaler.scales[domain]),
            )
            for domain in domains
        }
        for row in raw
    ]

    records: list[IngestRecord] = []
    for index, meta in enumerate(metadata):
        state = CardiacState(
            domain_scores=scores_by_sample[index],
            omics=ModalityVector(
                name="omics",
                values={"rna_module_features": float(len(domains))},
            ),
            time=meta.elapsed_hours,
            metadata={
                "subject_id": meta.subject_id,
                "experimental_unit_id": meta.subject_id,
                "sample_id": meta.sample_id,
                "condition_code": meta.condition_code,
                "replicate_index": "" if meta.replicate_index is None else str(meta.replicate_index),
                "dataset_id": "GSE144424",
                "module_scaler_fit_samples": str(len(scaler.fit_sample_ids)),
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


def parse_gse144424_count_metadata(sample_ids: Sequence[str]) -> tuple[GEOSampleMetadata, ...]:
    return tuple(parse_gse144424_count_column(sample_id) for sample_id in sample_ids)
