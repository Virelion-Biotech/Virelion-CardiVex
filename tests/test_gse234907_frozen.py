from pathlib import Path
import gzip

from cardivex.frozen_modules import FrozenModuleTransform
from cardivex.gse234907 import read_gse234907_heart_counts
from cardivex.gse234907_frozen import score_gse234907_with_frozen_transform


GENE_SETS = {
    "hypoxia_response": ("3091", "7422", "112399", "3939", "6513", "664", "133"),
    "inflammatory_response": ("3569", "3576", "6347", "4792", "7128", "5743", "3383"),
    "stress_response": ("1649", "468", "3309", "7494", "4189", "3162"),
    "contractile_maturation": ("7139", "7137", "4624", "4625", "70", "6262", "488"),
    "extracellular_matrix_remodeling": ("1277", "1278", "1281", "2335", "7040", "5054", "4313"),
}


def _fixture(path: Path) -> None:
    rows = [
        "#KEY\tS7_2\tS8_2\tS9_2\tS10_2\tS11_2\tS12_2",
        "#CLASS\t1021-2D\t1021-2D\t1021-2D\t1021-3D\t1021-3D\t1021-3D",
        "3091\t10\t20\t30\t40\t50\t60",
        "7422\t20\t30\t40\t50\t60\t70",
        "3569\t10\t20\t30\t40\t50\t60",
        "1649\t20\t30\t40\t50\t60\t70",
        "7139\t10\t20\t30\t40\t50\t60",
        "1277\t20\t30\t40\t50\t60\t70",
        "Geneid\tHISAT2 annotation\tHISAT2 annotation\tHISAT2 annotation\tHISAT2 annotation\tHISAT2 annotation\tHISAT2 annotation",
    ]
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("\n".join(rows) + "\n")


def _artifact() -> FrozenModuleTransform:
    domains = {name: tuple(values) for name, values in GENE_SETS.items()}
    centers = {name: 0.0 for name in domains}
    scales = {name: 1.0 for name in domains}
    return FrozenModuleTransform(
        artifact_version="0.1.0",
        dataset_id="GSE144424",
        source_file="source",
        source_sha256="sha",
        normalization="log1p(CPM) then development-only z-standardization and 0.15 scaling around 0.5",
        minimum_genes=1,
        domain_gene_sets=domains,
        centers=centers,
        scales=scales,
        fit_sample_ids=("development",),
        artifact_id="fixture",
    )


def test_gse234907_frozen_scorer_does_not_fit_external_data(tmp_path: Path) -> None:
    path = tmp_path / "counts.txt.gz"
    _fixture(path)
    matrix = read_gse234907_heart_counts(path)
    records = score_gse234907_with_frozen_transform(
        matrix,
        gene_sets=GENE_SETS,
        frozen_transform=_artifact(),
        minimum_genes=1,
    )
    assert len(records) == 6
    assert all(record.state.metadata["external_fit"] == "none" for record in records)
    assert all(record.state.domain_scores["hypoxia_response"] > 0.0 for record in records)
