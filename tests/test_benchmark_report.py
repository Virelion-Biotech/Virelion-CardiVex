import pytest

from cardivex.benchmark_factory import build_manifest
from cardivex.benchmark_report import compare_scenario_to_observation, summarize_manifest, summarize_observation_uncertainty
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState


def make_scenario(scenario_id: str, value: float, ood_status: str = "train") -> Scenario:
    domains = {"a": DomainValue(value, 0.1, "observed")}
    return Scenario(
        scenario_id=scenario_id,
        version="0.1.0",
        name="fixture",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.OBSERVED,
        confidence=Confidence.HIGH,
        phenotype_domains=domains,
        temporal_profile=(
            ScenarioState("onset", 0.0, domains),
            ScenarioState("peak", 1.0, domains),
        ),
        ood_status=ood_status,
        provenance_sources=("DS-TEST",),
        provenance_transformations=("observed_measurement",) if ood_status == "held_out_novel" else (),
    )


def test_summary_counts_development_and_holdout():
    train = make_scenario("CVX-1", 0.1)
    held = make_scenario("CVX-2", 0.9, "held_out_novel")
    summary = summarize_manifest(build_manifest([train, held]), train=[train], held_out=[held])
    assert summary.scenario_count == 2
    assert summary.held_out_count == 1
    assert summary.all_novel_held_out


def test_scenario_observation_error_is_transparent():
    scenario = make_scenario("CVX-3", 0.4)
    errors = compare_scenario_to_observation(scenario, {"a": 0.6})
    assert errors["mae"] == pytest.approx(0.2)
    assert errors["max_error"] == pytest.approx(0.2)


def test_observation_uncertainty_summary_contains_bounds():
    summary = summarize_observation_uncertainty([{"a": 0.2}, {"a": 0.4}])
    assert summary["a"]["mean"] == pytest.approx(0.3)
    assert summary["a"]["lower"] <= summary["a"]["mean"] <= summary["a"]["upper"]
