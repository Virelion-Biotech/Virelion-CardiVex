from cardivex.features import from_domain_scores
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.suite import build_run_audit, report_summary, run_benchmark_suite


def make_scenario(scenario_id: str, value: float, *, ood_status: str) -> Scenario:
    domain = {"inflammatory_activation": DomainValue(value, evidence_status="extrapolated")}
    states = (
        ScenarioState("onset", 0.0, {"inflammatory_activation": DomainValue(0.0)}),
        ScenarioState("peak", 1.0, domain),
    )
    return Scenario(
        scenario_id=scenario_id,
        version="0.1.0",
        name="suite scenario",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.EXPLORATORY,
        phenotype_domains=domain,
        temporal_profile=states,
        provenance_sources=("synthetic:test",),
        provenance_transformations=("test_transform",),
        validation_targets=("multimodal_state_consistency",),
        ood_status=ood_status,
    )


def test_suite_runs_and_reports_summary():
    scenarios = (
        make_scenario("CVX-9100", 0.1, ood_status="train"),
        make_scenario("CVX-9101", 0.2, ood_status="validation"),
        make_scenario("CVX-9102", 0.3, ood_status="test"),
        make_scenario("CVX-9103", 0.95, ood_status="held_out_novel"),
    )
    baseline = from_domain_scores({"inflammatory_activation": 0.0})
    known = [baseline]
    run = run_benchmark_suite(scenarios, baseline=baseline, known_states=known)
    assert all(item.status == "ok" for item in run.results)
    summary = report_summary(run)
    assert summary["scenario_count"] == 4
    assert summary["held_out_count"] == 1
    audit = build_run_audit(run, run_id="RUN-TEST", seed=7)
    assert audit["input_digest"]
