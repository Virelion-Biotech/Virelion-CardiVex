import json

from cardivex.features import from_domain_scores
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.serialization import dumps
from cardivex.suite import build_run_audit, run_benchmark_suite


def _scenario(scenario_id: str, status: str = "train", value: float = 0.5) -> Scenario:
    domain = {"inflammatory_activation": DomainValue(value)}
    states = (
        ScenarioState("baseline", 0.0, {"inflammatory_activation": DomainValue(0.0)}),
        ScenarioState("challenge", 1.0, domain),
    )
    return Scenario(
        scenario_id=scenario_id,
        version="0.1.0",
        name="suite fixture",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.MODERATE,
        phenotype_domains=domain,
        temporal_profile=states,
        provenance_sources=("DS-TEST",),
        provenance_transformations=("fixture",),
        ood_status=status,
    )


def test_benchmark_run_serializes_to_json():
    baseline = from_domain_scores({"inflammatory_activation": 0.0})
    scenarios = [
        _scenario("CVX-7001", value=0.5),
        _scenario("CVX-7002", "held_out_novel", value=1.0),
    ]
    run = run_benchmark_suite(scenarios, baseline=baseline, known_states=[baseline])
    payload = run.to_dict()
    decoded = json.loads(dumps(payload))
    assert decoded["name"] == "cardivex-benchmark"
    assert len(decoded["results"]) == 2
    assert decoded["results"][0]["score"] is not None


def test_run_audit_has_input_digest():
    baseline = from_domain_scores({"inflammatory_activation": 0.0})
    run = run_benchmark_suite([_scenario("CVX-7010")], baseline=baseline)
    audit = build_run_audit(run, run_id="RUN-1")
    assert len(audit["input_digest"]) == 64
