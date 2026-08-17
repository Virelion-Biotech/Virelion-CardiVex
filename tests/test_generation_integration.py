from cardivex.correlation import domain_correlation_matrix
from cardivex.ingest import ingest_processed_observation
from cardivex.phenotypes import fit_empirical_profile
from cardivex.scenario_builder import build_challenge_scenario, compose_novel_profile
from cardivex.pipeline import assess_scenario
from cardivex.features import from_domain_scores


def _records(condition: str, dataset: str, shift: float = 0.0):
    rows = []
    vals = (0.3, 0.45, 0.5, 0.6, 0.55, 0.4)
    for i, value in enumerate(vals, 1):
        rows.append(ingest_processed_observation(
            observation_id=f"{dataset}-{i}", dataset_id=dataset, condition=condition,
            time=float(i), domain_scores={
                "inflammatory_activation": min(1.0, value + shift),
                "contractile_impairment": min(1.0, value * 0.8 + shift * 0.5),
            },
        ))
    return rows


def test_correlation_matrix_is_symmetric_and_bounded():
    records = _records("challenge", "DS-CORR")
    matrix = domain_correlation_matrix(records, condition="challenge")
    assert set(matrix) == {"contractile_impairment", "inflammatory_activation"}
    assert matrix["contractile_impairment"]["inflammatory_activation"] == matrix["inflammatory_activation"]["contractile_impairment"]
    assert -1.0 <= matrix["contractile_impairment"]["inflammatory_activation"] <= 1.0


def test_novel_profile_and_pipeline_assessment():
    a_records = _records("a", "DS-A")
    b_records = _records("b", "DS-B", shift=0.1)
    pa = fit_empirical_profile(a_records, condition="a")
    pb = fit_empirical_profile(b_records, condition="b")
    combined = compose_novel_profile({"a": pa, "b": pb}, weights={"a": 0.4, "b": 0.6})
    assert set(combined) == set(pa.domains) | set(pb.domains)
    assert all(0.0 <= value <= 1.0 for value in combined.values())

    scenario = build_challenge_scenario(
        pa, scenario_id="CVX-9100", name="integration challenge",
        target_model="human_iPSC_derived_cardiac_tissue",
    )
    baseline = from_domain_scores({name: 0.0 for name in scenario.domain_vector()})
    assessment = assess_scenario(scenario, baseline=baseline)
    assert assessment.scenario_id == "CVX-9100"
    assert assessment.attribution
