from cardivex.engine import generate_variations, interpolate_timeline
from cardivex.models import DomainValue, Scenario, ScenarioState, EvidenceTier, Confidence


def make_scenario() -> Scenario:
    domains = {
        "inflammatory_activation": DomainValue(0.5, 0.1, "observed"),
        "contractile_impairment": DomainValue(0.4, 0.1, "proxy"),
    }
    states = (
        ScenarioState("onset", 0.0, domains),
        ScenarioState("peak", 2.0, {
            "inflammatory_activation": DomainValue(0.8),
            "contractile_impairment": DomainValue(0.7),
        }),
    )
    return Scenario(
        scenario_id="CVX-0001",
        version="0.1.0",
        name="test scenario",
        target_model="iPSC-derived cardiac model",
        evidence_tier=EvidenceTier.OBSERVED,
        confidence=Confidence.MODERATE,
        phenotype_domains=domains,
        temporal_profile=states,
        variation_space={"max_deviation": 0.1, "allowed_domains": list(domains)},
        provenance_sources=("synthetic:test",),
        provenance_transformations=(),
    )


def test_variations_are_bounded_and_traceable():
    scenario = make_scenario()
    variants = generate_variations(scenario, count=4, seed=42)
    assert len(variants) == 4
    assert variants[0].provenance_transformations
    for variant in variants:
        for value in variant.phenotype_domains.values():
            assert 0.0 <= value.value <= 1.0


def test_timeline_interpolation_is_monotonic_in_time():
    scenario = make_scenario()
    states = interpolate_timeline(scenario.temporal_profile, step=0.5)
    times = [state.relative_time for state in states]
    assert times == sorted(times)
    assert times[-1] == 2.0
