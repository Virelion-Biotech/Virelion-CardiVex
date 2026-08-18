from pathlib import Path
import gzip

from cardivex.gse234907 import read_gse234907_heart_counts, score_gse234907_modules, class_groups


def _fixture(path: Path) -> None:
    rows = [
        "#KEY\tS7_2\tS8_2\tS9_2\tS10_2\tS11_2\tS12_2",
        "#CLASS\t1021-2D\t1021-2D\t1021-2D\t1021-3D\t1021-3D\t1021-3D",
        "1\t10\t20\t30\t40\t50\t60",
        "2\t20\t30\t40\t50\t60\t70",
        "Geneid\tHISAT2 annotation\tHISAT2 annotation\tHISAT2 annotation\tHISAT2 annotation\tHISAT2 annotation\tHISAT2 annotation",
    ]
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("\n".join(rows) + "\n")


def test_read_gse234907_matrix(tmp_path: Path) -> None:
    path = tmp_path / "counts.txt.gz"
    _fixture(path)
    matrix = read_gse234907_heart_counts(path)
    assert matrix.sample_ids == ("S7_2", "S8_2", "S9_2", "S10_2", "S11_2", "S12_2")
    assert matrix.classes == ("1021-2D", "1021-2D", "1021-2D", "1021-3D", "1021-3D", "1021-3D")
    assert matrix.gene_ids == ("1", "2")
    assert len(matrix.counts) == 2


def test_score_gse234907_modules_remains_omics_only(tmp_path: Path) -> None:
    path = tmp_path / "counts.txt.gz"
    _fixture(path)
    matrix = read_gse234907_heart_counts(path)
    records = score_gse234907_modules(matrix, gene_sets={"module": ("1", "2")}, minimum_genes=2)
    assert len(records) == 6
    assert all(record.available_modalities == ("omics",) for record in records)
    assert class_groups(records)["1021-3D"] == ("S10_2", "S11_2", "S12_2")


def test_insufficient_gene_overlap_rejected(tmp_path: Path) -> None:
    path = tmp_path / "counts.txt.gz"
    _fixture(path)
    matrix = read_gse234907_heart_counts(path)
    try:
        score_gse234907_modules(matrix, gene_sets={"module": ("9999",)}, minimum_genes=1)
    except ValueError as exc:
        assert "insufficient overlap" in str(exc)
    else:
        raise AssertionError("expected insufficient-overlap error")
