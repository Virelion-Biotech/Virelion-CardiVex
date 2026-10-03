from cardivex.modeling import accuracy, fit_centroid_model
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.splits import make_split


def test_centroid_model_predicts_close_class():
    model = fit_centroid_model(
        [{"a": 0.0, "b": 0.1}, {"a": 0.1, "b": 0.0}, {"a": 0.9, "b": 0.8}],
        ["normal", "normal", "stressed"],
    )
    prediction = model.predict_one({"a": 0.05, "b": 0.05})
    assert prediction.label == "normal"
    assert prediction.confidence > 0.8


def test_accuracy():
    assert accuracy(["a", "b", "a"], ["a", "b", "b"]) == 2 / 3


def _scenario(scenario_id: str, status: str, value: float) -> Scenario:
    domain = {"stress": DomainValue(value, 0.05, "observed")}
    states = (
        ScenarioState("baseline", 0.0, domain),
        ScenarioState("peak", 1.0, domain),
    )
    return Scenario(
        scenario_id=scenario_id,
        version="0.1.0",
        name=scenario_id,
        target_model="cardiac_model",
        evidence_tier=EvidenceTier.OBSERVED,
        confidence=Confidence.MODERATE,
        phenotype_domains=domain,
        temporal_profile=states,
        provenance_sources=("test",),
        provenance_transformations=("test",),
        ood_status=status,
    )


def test_make_split_and_validate():
    split = make_split([
        _scenario("CVX-2001", "train", 0.1),
        _scenario("CVX-2002", "validation", 0.2),
        _scenario("CVX-2003", "test", 0.3),
        _scenario("CVX-2004", "held_out_novel", 0.9),
    ])
    assert len(split.train) == 1
    assert len(split.held_out_novel) == 1
