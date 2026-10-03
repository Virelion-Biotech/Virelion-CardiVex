from pathlib import Path
import gzip

import pytest

from cardivex.geo_counts import ModuleScoreConfig, parse_gse144424_metadata, read_geo_counts, score_count_modules


def _write_counts(path: Path) -> None:
    text = "gene\tGSM1\tGSM2\nG1\t10\t20\nG2\t10\t20\nG3\t5\t5\n"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)


def test_read_and_score_geo_counts(tmp_path: Path):
    path = tmp_path / "counts.txt.gz"
    _write_counts(path)
    matrix = read_geo_counts(path)
    metadata = parse_gse144424_metadata({
        "GSM1": "18499_A_RNA-seq",
        "GSM2": "18499_B_RNA-seq",
    })
    records = score_count_modules(
        matrix,
        metadata,
        ModuleScoreConfig(domain_gene_sets={"stress": ("G1", "G2")}),
    )
    assert [r.observation_id for r in records] == ["GSM1", "GSM2"]
    assert [r.time for r in records] == [0.0, 6.0]
    assert [r.available_modalities for r in records] == [("omics",), ("omics",)]
    assert records[0].state.metadata["subject_id"] == "18499"
    assert records[0].source_ref == "GEO:GSE144424:GSM1"


def test_metadata_column_order_must_match(tmp_path: Path):
    path = tmp_path / "counts.txt.gz"
    _write_counts(path)
    matrix = read_geo_counts(path)
    metadata = tuple(reversed(parse_gse144424_metadata({
        "GSM2": "18499_B_RNA-seq",
        "GSM1": "18499_A_RNA-seq",
    })))
    with pytest.raises(ValueError, match="must match count-matrix columns"):
        score_count_modules(matrix, metadata, ModuleScoreConfig(domain_gene_sets={"stress": ("G1", "G2")}))


def test_replicate_suffix_keeps_biological_subject():
    metadata = parse_gse144424_metadata({"GSM1": "18511_3_A_RNA-seq"})
    assert metadata[0].subject_id == "18511"
    assert metadata[0].elapsed_hours == 0.0
