from cardivex.challenge_families import build_combinatorial, build_severity_shift, build_temporal_shift, family_is_novel
from cardivex.ingest import ingest_processed_observation
from cardivex.phenotypes import fit_empirical_profile
from cardivex.scenario_builder import build_challenge_scenario


def profiles():
    def make(condition, offset):
        rows = [ingest_processed_observation(
            observation_id=f"{condition}-{i}", dataset_id="DS-FAM", condition=condition,
            time=float(i), domain_scores={"inflammatory_activation": 0.2 + offset + 0.03 * i,
                                          "contractile_impairment": 0.1 + offset + 0.02 * i})
            for i in range(1, 7)]
        return fit_empirical_profile(rows, condition=condition)
    return make("A", 0.0), make("B", 0.15)


def test_temporal_shift_changes_only_time():
    p, _ = profiles()
    base = build_challenge_scenario(p, scenario_id="CVX-8100", name="base", target_model="human_iPSC_derived_cardiac_tissue")
    shifted = build_temporal_shift(base, scenario_id="CVX-8101", time_scale=1.5)
    assert [s.domains for s in shifted.temporal_profile] == [s.domains for s in base.temporal_profile]
    assert shifted.temporal_profile[-1].relative_time > base.temporal_profile[-1].relative_time


def test_combinatorial_is_extrapolated_and_held_out():
    a, b = profiles()
    scenario = build_combinatorial({"a": a, "b": b}, weights={"a": 0.5, "b": 0.5}, scenario_id="CVX-8102")
    assert scenario.evidence_tier.value == "extrapolated"
    assert scenario.ood_status == "held_out_novel"


def test_family_novelty_uses_known_vectors():
    a, _ = profiles()
    known = build_challenge_scenario(a, scenario_id="CVX-8103", name="known", target_model="human_iPSC_derived_cardiac_tissue")
    candidate = build_severity_shift(a, scenario_id="CVX-8104", scale=1.4)
    assert isinstance(family_is_novel(candidate, [known]), bool)
