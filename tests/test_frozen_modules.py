from __future__ import annotations

import pytest

from cardivex.frozen_modules import FrozenModuleTransform, require_complete_frozen_transform


def test_incomplete_transform_is_rejected_before_external_scoring():
    artifact = FrozenModuleTransform(
        artifact_version="0.1.0",
        dataset_id="GSE144424",
        source_file="GSE144424_Counts_RNA_MCW_NEB.txt.gz",
        source_sha256="cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c",
        normalization="log1p(CPM) then development-only z-standardization and 0.15 scaling around 0.5",
        minimum_genes=3,
        domain_gene_sets={"hypoxia_response": ("HIF1A",)},
        centers={},
        scales={},
        fit_sample_ids=(),
        artifact_id="pending",
    )
    with pytest.raises(ValueError, match="fitted centers/scales are required"):
        require_complete_frozen_transform(artifact)


def test_complete_transform_applies_without_fitting():
    artifact = FrozenModuleTransform(
        artifact_version="0.1.0",
        dataset_id="GSE144424",
        source_file="source",
        source_sha256="abc",
        normalization="log1p(CPM) then development-only z-standardization and 0.15 scaling around 0.5",
        minimum_genes=1,
        domain_gene_sets={"a": ("A",)},
        centers={"a": 10.0},
        scales={"a": 2.0},
        fit_sample_ids=("S1",),
        artifact_id="x",
    )
    require_complete_frozen_transform(artifact)
    assert artifact.apply(({"a": 12.0},))[0]["a"] == pytest.approx(0.65)
