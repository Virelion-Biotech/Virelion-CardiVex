from cardivex.ingest import ingest_processed_observation
from cardivex.phenotypes import fit_empirical_profile
from cardivex.scenario_builder import ScenarioBuildConfig, build_challenge_scenario
from cardivex.trajectory import bounded_trajectory, shift_timeline
from cardivex.novelty import is_novel


def _records():
    rows = []
    for i, value in enumerate((0.4, 0.5, 0.6, 0.55, 0.45, 0.5), 1):
        rows.append(ingest_processed_observation(
            observation_id=f"obs-{i}", dataset_id="DS-TEST", condition="challenge_proxy",
            time=float(i), domain_scores={"inflammatory_activation": value, "contractile_impairment": value * 0.8},
        ))
    return rows


def test_empirical_profile_and_builder_are_traceable():
    profile = fit_empirical_profile(_records(), condition="challenge_proxy")
    scenario = build_challenge_scenario(
        profile,
        scenario_id="CVX-9001",
        name="empirical benchmark scenario",
        target_model="human_iPSC_derived_cardiac_tissue",
        config=ScenarioBuildConfig(seed=11),
    )
    assert scenario.provenance_sources == ("DS-TEST",)
    assert scenario.provenance_transformations
    assert scenario.ood_status == "held_out_novel"
    assert len(scenario.temporal_profile) == 3


def test_trajectory_is_bounded_and_time_shifted():
    states = bounded_trajectory({"a": 0.8, "b": 0.4}, recovery_fraction=0.25)
    shifted = shift_timeline(states, scale=1.5)
    assert shifted[-1].relative_time > states[-1].relative_time
    assert all(0.0 <= v.value <= 1.0 for s in shifted for v in s.domains.values())


def test_novelty_rejects_distant_candidate():
    assert is_novel({"a": 1.0, "b": 1.0}, [{"a": 0.0, "b": 0.0}], threshold=0.5)
