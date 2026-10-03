import pytest

from cardivex.geo_metadata import parse_gse144424_sample_title


def test_parse_standard_gse144424_sample():
    item = parse_gse144424_sample_title("GSM4287987", "18499_A_RNA-seq")
    assert item.subject_id == "18499"
    assert item.condition == "normoxia"
    assert item.elapsed_hours == 0.0
    assert item.modality == "rna_seq"


def test_parse_replicated_subject_keeps_subject_identity():
    item = parse_gse144424_sample_title("GSM4288047", "18511_2_A_RNA-seq")
    assert item.subject_id == "18511"
    assert item.condition_code == "A"


def test_parse_reoxygenation_timepoints():
    early = parse_gse144424_sample_title("GSM4287989", "18499_C_RNA-seq")
    late = parse_gse144424_sample_title("GSM4287990", "18499_D_RNA-seq")
    assert early.condition == "reoxygenation_1"
    assert early.elapsed_hours == 12.0
    assert late.condition == "reoxygenation_2"
    assert late.elapsed_hours == 30.0


def test_rejects_unknown_title():
    with pytest.raises(ValueError):
        parse_gse144424_sample_title("GSM-X", "unexpected_sample")
