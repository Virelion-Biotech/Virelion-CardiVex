import pytest

from cardivex.ingest import ingest_processed_observation, require_modalities


def test_ingest_preserves_provenance_and_modalities():
    record = ingest_processed_observation(
        observation_id="OBS-001",
        dataset_id="DS-0001",
        condition="challenge_proxy",
        time=2.0,
        domain_scores={"inflammatory_activation": 0.6},
        imaging={"morphology": 0.4},
        functional={"contractility": 0.7},
        source_ref="example://obs-001",
    )
    assert record.available_modalities == ("imaging", "functional")
    assert record.state.metadata["dataset_id"] == "DS-0001"
    assert record.state.metadata["source_ref"] == "example://obs-001"


def test_require_modalities_rejects_missing_data():
    record = ingest_processed_observation(
        observation_id="OBS-002",
        dataset_id="DS-0001",
        condition="baseline",
        time=0.0,
        domain_scores={"x": 0.1},
        omics={"signature": 0.2},
    )
    with pytest.raises(ValueError, match="missing required modalities"):
        require_modalities(record, ["imaging", "omics"])


def test_negative_time_is_rejected():
    with pytest.raises(ValueError):
        ingest_processed_observation(
            observation_id="OBS-003",
            dataset_id="DS-0001",
            condition="baseline",
            time=-1,
            domain_scores={"x": 0.1},
        )
