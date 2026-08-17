import pytest

from cardivex.calibration_runner import build_development_calibration, calibration_json
from cardivex.data_plan import build_analysis_plan
from cardivex.ingest import ingest_processed_observation


def _records():
    rows = []
    for unit in ("U1", "U2", "U3", "U4"):
        for time, value in ((0.0, 0.1), (1.0, 0.3)):
            record = ingest_processed_observation(
                observation_id=f"{unit}-{int(time)}",
                dataset_id="DS-CAL",
                condition="challenge",
                time=time,
                domain_scores={"inflammatory_activation": value, "contractile_impairment": value / 2},
                imaging={"inflammatory_signal": value},
                functional={"contractile_signal": 1.0 - value},
                omics={"inflammatory_signature": value},
                source_ref="fixture",
            )
            state = type(record.state)(
                imaging=record.state.imaging,
                functional=record.state.functional,
                omics=record.state.omics,
                domain_scores=record.state.domain_scores,
                time=record.state.time,
                metadata={**record.state.metadata, "experimental_unit_id": unit},
            )
            rows.append(type(record)(
                observation_id=record.observation_id,
                dataset_id=record.dataset_id,
                condition=record.condition,
                time=record.time,
                state=state,
                available_modalities=record.available_modalities,
                source_ref=record.source_ref,
            ))
    return rows


def test_calibration_excludes_holdout_groups_from_all_fit_components():
    records = _records()
    plan = build_analysis_plan(records, required_modalities=("imaging", "functional", "omics"), min_holdout_groups=1)
    artifact = build_development_calibration(records, plan)
    assert artifact.held_out_group_ids == plan.held_out_candidate_group_ids
    assert not set(artifact.excluded_record_ids) & set(artifact.development_record_ids)
    assert artifact.translation is not None
    assert artifact.condition_calibrations[0].temporal is not None
    assert artifact.condition_calibrations[0].correlation
    assert artifact.artifact_id
    assert "artifact_id" in calibration_json(artifact)


def test_calibration_rejects_mismatched_dataset():
    records = _records()
    plan = build_analysis_plan(records, required_modalities=("imaging", "functional", "omics"), min_holdout_groups=1)
    bad = [type(records[0])(
        observation_id=records[0].observation_id,
        dataset_id="OTHER",
        condition=records[0].condition,
        time=records[0].time,
        state=records[0].state,
        available_modalities=records[0].available_modalities,
        source_ref=records[0].source_ref,
    )]
    with pytest.raises(ValueError, match="analysis plan dataset"):
        build_development_calibration(bad, plan)
