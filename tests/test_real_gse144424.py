from pathlib import Path
import gzip

import pytest

from cardivex.geo_counts import ModuleScoreConfig, fit_module_scaler, parse_gse144424_count_metadata, read_geo_counts, score_count_modules
from cardivex.longitudinal import collapse_subject_replicates, group_longitudinal_records


def _write_annotation_counts(path: Path) -> None:
    text = (
        "Geneid\tChr\tStart\tEnd\tStrand\tLength\tH18499_A\tH18499_B\tH18499_2_A\tH18499_2_B\n"
        "ENSG00000100644\tchr14\t1\t2\t+\t100\t100\t200\t120\t220\n"
        "ENSG00000112715\tchr6\t1\t2\t+\t100\t100\t200\t120\t220\n"
        "ENSG00000147813\tchr14\t1\t2\t+\t100\t100\t200\t120\t220\n"
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)


def test_gse_count_columns_parse_and_retain_subject(tmp_path: Path):
    path = tmp_path / "counts.txt.gz"
    _write_annotation_counts(path)
    matrix = read_geo_counts(path)
    assert matrix.sample_ids == ("H18499_A", "H18499_B", "H18499_2_A", "H18499_2_B")
    metadata = parse_gse144424_count_metadata(matrix.sample_ids)
    assert metadata[2].subject_id == "18499"
    assert metadata[2].replicate_index == 2


def test_scaler_fit_can_be_development_only(tmp_path: Path):
    path = tmp_path / "counts.txt.gz"
    _write_annotation_counts(path)
    matrix = read_geo_counts(path)
    metadata = parse_gse144424_count_metadata(matrix.sample_ids)
    config = ModuleScoreConfig(domain_gene_sets={"hypoxia": (
        "ENSG00000100644", "ENSG00000112715", "ENSG00000147813"),})
    scaler = fit_module_scaler(matrix, config, fit_sample_ids=("H18499_A", "H18499_2_A"))
    assert scaler.fit_sample_ids == ("H18499_2_A", "H18499_A")
    records = score_count_modules(matrix, metadata, config, scaler=scaler)
    assert all("experimental_unit_id" in r.state.metadata for r in records)
    assert all(r.available_modalities == ("omics",) for r in records)


def test_collapse_subject_replicates():
    path = Path("/tmp/cardivex-real-test-counts.gz")
    _write_annotation_counts(path)
    matrix = read_geo_counts(path)
    metadata = parse_gse144424_count_metadata(matrix.sample_ids)
    config = ModuleScoreConfig(domain_gene_sets={"hypoxia": (
        "ENSG00000100644", "ENSG00000112715", "ENSG00000147813"),})
    records = score_count_modules(matrix, metadata, config)
    collapsed = collapse_subject_replicates(records)
    groups = group_longitudinal_records(collapsed)
    assert len(collapsed) == 2
    assert len(groups) == 1
    assert len(groups[0].records) == 2
    assert groups[0].records[0].state.metadata["collapsed_replicates"] == "2"


def test_count_reader_rejects_negative_values(tmp_path: Path):
    path = tmp_path / "bad.txt.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("Geneid\tChr\tStart\tEnd\tStrand\tLength\tH18499_A\nG\tchr1\t1\t2\t+\t10\t-1\n")
    with pytest.raises(ValueError, match="negative count"):
        read_geo_counts(path)
