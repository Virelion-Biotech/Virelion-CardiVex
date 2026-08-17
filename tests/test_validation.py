from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.validation import detect_direct_leakage, validate_scenario


def make_scenario(scenario_id: str, *, ood_status: str = "train") -> Scenario:
    domain = {"inflammatory_activation": DomainValue(0.4, evidence_status="observed")}
    states = (
        ScenarioState("baseline", 0.0, domain),
        ScenarioState("peak", 1.0, domain),
    )
    return Scenario(
        scenario_id=scenario_id,
        version="0.1.0",
        name="validation scenario",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.OBSERVED,
        confidence=Confidence.MODERATE,
        phenotype_domains=domain,
        temporal_profile=states,
        provenance_sources=("test",),
        provenance_transformations=("test",),
        ood_status=ood_status,
    )


def test_held_out_duplicate_is_detected():
    train = [make_scenario("CVX-1000")]
    held_out = [make_scenario("CVX-1001", ood_status="held_out_novel")]
    issues = detect_direct_leakage(train, held_out)
    assert any(issue.code == "VECTOR_LEAK" for issue in issues)


def test_valid_observed_scenario_has_no_issues():
    scenario = make_scenario("CVX-1002")
    assert validate_scenario(scenario) == []


def test_missing_transform_trace_is_rejected():
    scenario = make_scenario("CVX-1003")
    broken = Scenario(
        scenario_id=scenario.scenario_id,
        version=scenario.version,
        name=scenario.name,
        target_model=scenario.target_model,
        evidence_tier=scenario.evidence_tier,
        confidence=scenario.confidence,
        phenotype_domains=scenario.phenotype_domains,
        temporal_profile=scenario.temporal_profile,
        provenance_sources=scenario.provenance_sources,
        provenance_transformations=(),
        ood_status=scenario.ood_status,
    )
    assert any(issue.code == "MISSING_TRANSFORM_TRACE" for issue in validate_scenario(broken))
