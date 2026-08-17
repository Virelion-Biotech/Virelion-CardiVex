import pytest

from cardivex.physiology import (
    GSE234907Observation,
    PhysiologicalFeatureConfig,
    ingest_gse234907_physiology,
    normalize_physiology,
)


def _configs():
    return (
        PhysiologicalFeatureConfig("oxygen_uptake", "oxygen_uptake", 0.0, 10.0),
        PhysiologicalFeatureConfig("field_potential_duration", "field_potential_duration", 100.0, 500.0),
        PhysiologicalFeatureConfig("contraction_amplitude", "contraction_amplitude", 0.0, 1.0, inverse=True),
    )


def test_normalize_physiology_is_explicit_and_bounded():
    result = normalize_physiology(
        {"oxygen_uptake": 5.0, "field_potential_duration": 300.0, "contraction_amplitude": 0.25},
        _configs(),
    )
    assert result["oxygen_uptake"] == pytest.approx(0.5)
    assert result["field_potential_duration"] == pytest.approx(0.5)
    assert result["contraction_amplitude"] == pytest.approx(0.75)


def test_ingest_preserves_experimental_unit_and_functional_only():
    observations = (
        GSE234907Observation(
            observation_id="CVX-GSE234907-1",
            experimental_unit="ORG-1",
            condition="vascularized_organoid",
            time=25.0,
            measurements={"oxygen_uptake": 5.0, "field_potential_duration": 300.0},
            source_ref="GSE234907:processed_sensor_table",
        ),
    )
    records = ingest_gse234907_physiology(observations, _configs())
    assert len(records) == 1
    assert records[0].available_modalities == ("functional",)
    assert records[0].state.metadata["experimental_unit"] == "ORG-1"
    assert set(records[0].state.imaging.values) == set()
    assert records[0].source_ref.startswith("GSE234907")


def test_duplicate_observation_ids_are_rejected():
    observation = GSE234907Observation(
        "CVX-GSE234907-1", "ORG-1", "vascularized_organoid", 25.0,
        {"oxygen_uptake": 5.0}, "GSE234907:test",
    )
    with pytest.raises(ValueError, match="duplicate observation ID"):
        ingest_gse234907_physiology((observation, observation), _configs())
