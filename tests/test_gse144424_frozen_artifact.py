from __future__ import annotations

import pytest

from cardivex.frozen_modules import FrozenModuleTransform, compute_artifact_id, require_complete_frozen_transform
from cardivex.geo_counts import ModuleScoreScaler


ARTIFACT_ID = "27a6554942da99ba"
CENTERS = {
    "hypoxia_response": 5.943568072823221,
    "inflammatory_response": 2.031578586172451,
    "stress_response": 4.453042806259525,
    "contractile_maturation": 7.763700331112314,
    "extracellular_matrix_remodeling": 5.885868277196324,
}
SCALES = {
    "hypoxia_response": 0.5786549043876493,
    "inflammatory_response": 0.711188636036,
    "stress_response": 0.48815295451044377,
    "contractile_maturation": 0.34265313032174183,
    "extracellular_matrix_remodeling": 1.2833733325723107,
}
DOMAINS = {
    "hypoxia_response": ("ENSG00000100644", "ENSG00000112715", "ENSG00000129521", "ENSG00000134333", "ENSG00000117394", "ENSG00000176171", "ENSG00000148926"),
    "inflammatory_response": ("ENSG00000136244", "ENSG00000169429", "ENSG00000108691", "ENSG00000100906", "ENSG00000118503", "ENSG00000073756", "ENSG00000090339"),
    "stress_response": ("ENSG00000175197", "ENSG00000128272", "ENSG00000044574", "ENSG00000100219", "ENSG00000116193", "ENSG00000100292"),
    "contractile_maturation": ("ENSG00000118194", "ENSG00000129991", "ENSG00000197616", "ENSG00000092054", "ENSG00000159251", "ENSG00000198626", "ENSG00000174437"),
    "extracellular_matrix_remodeling": ("ENSG00000108821", "ENSG00000164692", "ENSG00000168542", "ENSG00000115414", "ENSG00000105329", "ENSG00000106366", "ENSG00000087245"),
}
FIT_SAMPLE_IDS = (
    "H18499_A", "H18499_B", "H18499_C", "H18499_D", "H18505_A", "H18505_B", "H18505_C", "H18505_D",
    "H18511_2_A", "H18511_2_B", "H18511_2_C", "H18511_2_D", "H18511_3_A", "H18511_3_B", "H18511_3_C", "H18511_3_D",
    "H18511_A", "H18511_B", "H18511_C", "H18511_D", "H18520_A", "H18520_B", "H18520_C", "H18520_D",
    "H18852_2_A", "H18852_2_B", "H18852_2_C", "H18852_2_D", "H18852_3_A", "H18852_3_B", "H18852_3_C", "H18852_3_D",
    "H18852_A", "H18852_B", "H18852_C", "H18852_D", "H18858_A", "H18858_B", "H18858_C", "H18858_D",
    "H18912_A", "H18912_B", "H18912_C", "H18912_D", "H19098_A", "H19098_B", "H19098_C", "H19098_D",
    "H19101_A", "H19101_B", "H19101_C", "H19101_D", "H19108_A", "H19108_B", "H19108_C", "H19108_D",
    "H19116_A", "H19116_B", "H19116_C", "H19116_D", "H19160_A", "H19160_B", "H19160_C", "H19160_D",
)


def test_corrected_gse144424_frozen_parameters_are_complete_and_stable():
    scaler = ModuleScoreScaler(centers=CENTERS, scales=SCALES, fit_sample_ids=FIT_SAMPLE_IDS)
    assert compute_artifact_id(
        dataset_id="GSE144424",
        source_file="GSE144424_Counts_RNA_MCW_NEB.txt.gz",
        source_sha256="cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c",
        normalization="log1p(CPM) then development-only z-standardization and 0.15 scaling around 0.5",
        minimum_genes=3,
        domain_gene_sets=DOMAINS,
        scaler=scaler,
        artifact_version="0.2.0",
    ) == ARTIFACT_ID

    artifact = FrozenModuleTransform(
        artifact_version="0.2.0",
        dataset_id="GSE144424",
        source_file="GSE144424_Counts_RNA_MCW_NEB.txt.gz",
        source_sha256="cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c",
        normalization="log1p(CPM) then development-only z-standardization and 0.15 scaling around 0.5",
        minimum_genes=3,
        domain_gene_sets=DOMAINS,
        centers=CENTERS,
        scales=SCALES,
        fit_sample_ids=FIT_SAMPLE_IDS,
        artifact_id=ARTIFACT_ID,
    )
    require_complete_frozen_transform(artifact)
    assert artifact.apply((CENTERS,))[0] == pytest.approx({domain: 0.5 for domain in CENTERS})
