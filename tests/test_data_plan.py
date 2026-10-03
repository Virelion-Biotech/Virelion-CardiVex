import pytest

from cardivex.data_plan import build_analysis_plan
from cardivex.ingest import ingest_processed_observation


def _records():
    rows = []
    for group_id, prefix in (("G1", "A"), ("G2", "B")):
        for idx, value in enumerate((0.1, 0.4)):
            record = ingest_processed_observation(
                observation_id=f"{prefix}-{idx}",
                dataset_id="DS-PLAN",
                condition="challenge",
                time=float(idx),
                domain_scores={"inflammatory_activation": value},
                imaging={"signal": value},
                functional={"contractility": 1.0 - value},
                omics={"signature": value},
                source_ref="fixture",
            )
            state = type(record.state)(
                imaging=record.state.imaging,
                functional=record.state.functional,
                omics=record.state.omics,
                domain_scores=record.state.domain_scores,
                time=record.state.time,
                metadata={**record.state.metadata, "experimental_unit_id": group_id},
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


def test_build_analysis_plan_is_deterministic():
    plan = build_analysis_plan(_records(), expected_times=(0.0, 1.0))
    assert plan.dataset_id == "DS-PLAN"
    assert plan.longitudinal_group_ids == ("G1", "G2")
    assert len(plan.multimodal_record_ids) == 4
    assert plan.held_out_candidate_group_ids == ("G2",)
    assert plan.qualification.recommended_uses


def test_analysis_plan_rejects_unqualified_dataset():
    record = ingest_processed_observation(
        observation_id="ONLY-1",
        dataset_id="DS-BAD",
        condition="challenge",
        time=0.0,
        domain_scores={"inflammatory_activation": 0.2},
    )
    with pytest.raises(ValueError, match="not qualified"):
        build_analysis_plan([record], expected_times=(0.0, 1.0))
