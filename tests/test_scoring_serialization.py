from cardivex.features import from_domain_scores
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.pipeline import assess_scenario
from cardivex.scoring import score_assessment, score_modalities
from cardivex.serialization import dumps


def _scenario():
    domain = {"inflammatory_activation": DomainValue(0.7), "contractile_impairment": DomainValue(0.6)}
    states = (
        ScenarioState("baseline", 0.0, {k: DomainValue(0.0) for k in domain}),
        ScenarioState("challenge", 1.0, domain),
    )
    return Scenario(
        scenario_id="CVX-5001",
        version="0.1.0",
        name="serialization test",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.MODERATE,
        phenotype_domains=domain,
        temporal_profile=states,
        provenance_sources=("DS-TEST",),
        provenance_transformations=("test",),
        ood_status="held_out_novel",
    )


def test_modalities_and_assessment_score():
    baseline = from_domain_scores(
        {"inflammatory_activation": 0.0, "contractile_impairment": 0.0},
        imaging={"texture": 0.1}, functional={"contractility": 0.1},
    )
    assessment = assess_scenario(_scenario(), baseline=baseline, known_states=[baseline])
    score = score_assessment(assessment, baseline=baseline, known_states=[baseline])
    assert score.overall_abnormality > 0
    assert len(score.modality_scores) == 3


def test_serialization_is_valid_json():
    payload = {"assessment": score_assessment(
        assess_scenario(_scenario(), baseline=from_domain_scores({"inflammatory_activation": 0.0})),
        baseline=from_domain_scores({"inflammatory_activation": 0.0}),
    )}
    text = dumps(payload)
    assert '"assessment"' in text
    assert "NaN" not in text
