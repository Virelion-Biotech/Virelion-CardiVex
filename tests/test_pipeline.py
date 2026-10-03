from cardivex.features import from_domain_scores
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.pipeline import assess_scenario, run_end_to_end


def make_scenario() -> Scenario:
    domains = {
        "inflammatory_activation": DomainValue(0.8),
        "contractile_impairment": DomainValue(0.7),
        "mitochondrial_dysfunction": DomainValue(0.6),
        "structural_disorganization": DomainValue(0.4),
    }
    return Scenario(
        scenario_id="CVX-0091",
        version="0.1.0",
        name="synthetic multimodal challenge",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.EXPLORATORY,
        phenotype_domains=domains,
        temporal_profile=(
            ScenarioState("baseline", 0.0, {}),
            ScenarioState("peak", 1.0, domains),
        ),
        provenance_sources=("synthetic:test",),
        provenance_transformations=("bounded:test",),
    )


def test_assessment_runs_end_to_end():
    baseline = from_domain_scores(
        {"inflammatory_activation": 0.0, "contractile_impairment": 0.0,
         "mitochondrial_dysfunction": 0.0, "structural_disorganization": 0.0},
        imaging={"structure": 0.0},
        functional={"contractility": 0.0},
        omics={"inflammation": 0.0},
    )
    assessment = assess_scenario(make_scenario(), baseline=baseline)
    assert assessment.detection.is_abnormal
    assert len(assessment.attribution) == 4
    assert assessment.challenged_state.functional is not None


def test_recovery_is_attached_when_treatment_is_supplied():
    baseline = from_domain_scores(
        {"inflammatory_activation": 0.0, "contractile_impairment": 0.0,
         "mitochondrial_dysfunction": 0.0, "structural_disorganization": 0.0},
        imaging={"structure": 0.0}, functional={"contractility": 0.0}, omics={"inflammation": 0.0},
    )
    treated = from_domain_scores(
        {"inflammatory_activation": 0.2, "contractile_impairment": 0.2,
         "mitochondrial_dysfunction": 0.2, "structural_disorganization": 0.1},
        imaging={"structure": 0.1}, functional={"contractility": 0.1}, omics={"inflammation": 0.1},
    )
    result = run_end_to_end(make_scenario(), baseline=baseline, treated_state=treated)
    assert result.recovery is not None
    assert result.recovery.overall > 0.0
