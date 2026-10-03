from __future__ import annotations

from typing import Mapping, Sequence

from .features import CardiacState, ModalityVector
from .frozen_modules import FrozenModuleTransform, require_complete_frozen_transform
from .gse234907 import GSE234907Matrix, _log_cpm
from .ingest import IngestRecord


def score_gse234907_with_frozen_transform(
    matrix: GSE234907Matrix,
    *,
    gene_sets: Mapping[str, Sequence[str]],
    frozen_transform: FrozenModuleTransform,
    minimum_genes: int = 3,
) -> tuple[IngestRecord, ...]:
    """Score all GSE234907 samples with a frozen reference transform.

    The gene sets identify the raw external matrix IDs (Entrez IDs in the
    uploaded GSE234907 Heart_counts matrix). The reference transform supplies
    the development-only centers/scales; no external fitting is performed.
    """
    require_complete_frozen_transform(frozen_transform)
    if set(gene_sets) != set(frozen_transform.domain_gene_sets):
        raise ValueError("external gene-set domains do not match frozen transform domains")
    if minimum_genes < 1:
        raise ValueError("minimum_genes must be positive")

    expression = _log_cpm(matrix)
    raw_rows: list[dict[str, float]] = []
    for index, sample_id in enumerate(matrix.sample_ids):
        row: dict[str, float] = {}
        for domain, genes in gene_sets.items():
            values = [expression[index][gene] for gene in genes if gene in expression[index]]
            if len(values) < minimum_genes:
                raise ValueError(f"gene set '{domain}' has insufficient overlap in sample {sample_id}")
            row[domain] = sum(values) / len(values)
        raw_rows.append(row)

    frozen_scores = frozen_transform.apply(raw_rows)
    records: list[IngestRecord] = []
    for index, sample_id in enumerate(matrix.sample_ids):
        scores = frozen_scores[index]
        state = CardiacState(
            domain_scores=scores,
            omics=ModalityVector("omics", {"rna_module_features": 1.0 if scores else 0.0}),
            time=0.0,
            metadata={
                "experimental_unit_id": sample_id,
                "sample_id": sample_id,
                "gse234907_class": matrix.classes[index],
                "dataset_id": "GSE234907",
                "transform_artifact_id": frozen_transform.artifact_id,
                "transform_source_dataset": frozen_transform.dataset_id,
                "external_fit": "none",
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
