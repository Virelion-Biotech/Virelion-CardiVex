from cardivex.ingest import ingest_processed_observation
from cardivex.longitudinal import group_longitudinal_records, validate_disjoint_longitudinal_groups


def _record(obs, unit):
    record = ingest_processed_observation(
        observation_id=obs,
        dataset_id="DS-SPLIT",
        condition="challenge",
        time=0.0,
        domain_scores={"inflammatory_activation": 0.2},
    )
    return type(record)(
        observation_id=record.observation_id,
        dataset_id=record.dataset_id,
        condition=record.condition,
        time=record.time,
        state=type(record.state)(
            imaging=record.state.imaging,
            functional=record.state.functional,
            omics=record.state.omics,
            domain_scores=record.state.domain_scores,
            time=record.state.time,
            metadata={**record.state.metadata, "experimental_unit_id": unit},
        ),
        available_modalities=record.available_modalities,
        source_ref=record.source_ref,
    )


def test_experimental_units_must_be_disjoint_across_evaluation_sets():
    development = group_longitudinal_records([_record("D1", "U1"), _record("D2", "U2")])
    held_out = group_longitudinal_records([_record("H1", "U2"), _record("H2", "U3")])
    assert validate_disjoint_longitudinal_groups(development, held_out) == ("U2",)


def test_disjoint_groups_have_no_overlap():
    development = group_longitudinal_records([_record("D1", "U1")])
    held_out = group_longitudinal_records([_record("H1", "U2")])
    assert validate_disjoint_longitudinal_groups(development, held_out) == ()
