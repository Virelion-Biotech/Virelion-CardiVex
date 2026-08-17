import pytest

from cardivex.ingest import ingest_processed_observation
from cardivex.temporal import fit_temporal_profile, materialize_trajectory
from cardivex.phenotypes import fit_empirical_profile
from cardivex.scenario_builder import ScenarioBuildConfig, build_challenge_scenario


def _records():
    rows = []
    for idx, (time, value_a, value_b) in enumerate(
        [(0.0, 0.1, 0.2), (1.0, 0.4, 0.3), (2.0, 0.8, 0.6), (3.0, 0.5, 0.4)],
        1,
    ):
        rows.append(
            ingest_processed_observation(
                observation_id=f"OBS-{idx}",
                dataset_id="DS-TEMP",
                condition="challenge",
                time=time,
                domain_scores={"a": value_a, "b": value_b},
            )
        )
    return rows


def test_fit_temporal_profile_preserves_order_and_normalizes_time():
    profile = fit_temporal_profile(_records(), condition="challenge")
    assert tuple(point.relative_time for point in profile.points) == (0.0, 1 / 3, 2 / 3, 1.0)
    assert profile.domain_names == ("a", "b")
    assert profile.source_dataset_ids == ("DS-TEMP",)


def test_materialize_trajectory_applies_explicit_scales():
    profile = fit_temporal_profile(_records(), condition="challenge")
    states = materialize_trajectory(profile, severity_scale=0.5, time_scale=2.0)
    assert states[0].relative_time == 0.0
    assert states[-1].relative_time == 2.0
    assert states[2].domains["a"].value == pytest.approx(0.4)
    assert states[2].domains["a"].evidence_status == "extrapolated"


def test_builder_records_empirical_temporal_lineage():
    records = _records()
    empirical = fit_empirical_profile(records, condition="challenge")
    temporal = fit_temporal_profile(records, condition="challenge")
    scenario = build_challenge_scenario(
        empirical,
        scenario_id="CVX-9200",
        name="temporal integration challenge",
        target_model="human_iPSC_derived_cardiac_tissue",
        config=ScenarioBuildConfig(temporal_severity_scale=0.8, temporal_time_scale=1.5),
        temporal_profile=temporal,
    )
    assert scenario.variation_space["temporal_empirical"] is True
    assert "empirical_temporal_profile_fit" in scenario.provenance_transformations
    assert scenario.temporal_profile[-1].relative_time == pytest.approx(1.5)
