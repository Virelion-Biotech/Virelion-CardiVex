import pytest

from cardivex.features import CardiacState
from cardivex.geo_counts import GEOCountMatrix, ModuleScoreConfig
from cardivex.geo_metadata import GEOSampleMetadata
from cardivex.ingest import IngestRecord
from cardivex.real_data_pipeline import build_subject_disjoint_split, collapse_replicates


def test_subject_disjoint_split():
    metadata = (
        GEOSampleMetadata("A", "S1", "A", "normoxia", 0.0, "rna_seq", None),
        GEOSampleMetadata("B", "S1", "B", "hypoxia", 6.0, "rna_seq", None),
        GEOSampleMetadata("C", "S2", "A", "normoxia", 0.0, "rna_seq", None),
        GEOSampleMetadata("D", "S2", "B", "hypoxia", 6.0, "rna_seq", None),
    )
    split = build_subject_disjoint_split(metadata, held_out_subjects=["S2"])
    assert split.development_sample_ids == ("A", "B")
    assert split.held_out_sample_ids == ("C", "D")


def test_replicate_collapse_preserves_provenance():
    rows = []
    for sample_id, value in (("S1_rep1_A", 0.2), ("S1_rep2_A", 0.6)):
        rows.append(IngestRecord(
            observation_id=sample_id,
            dataset_id="TEST",
            condition="normoxia",
            time=0.0,
            state=CardiacState(
                domain_scores={"stress": value},
                metadata={"experimental_unit_id": "S1"},
            ),
            available_modalities=(),
        ))
    collapsed = collapse_replicates(rows)
    assert len(collapsed) == 1
    assert collapsed[0].state.domain_scores["stress"] == pytest.approx(0.4)
    assert collapsed[0].state.metadata["collapsed_replicate_count"] == "2"
    assert "S1_rep1_A" in collapsed[0].state.metadata["collapsed_sample_ids"]
