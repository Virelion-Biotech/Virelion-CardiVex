from cardivex.audit import build_audit_record
from cardivex.defense import abnormality_score, nearest_state_distance, rescue_score


def test_abnormality_zero_for_baseline():
    state = {"a": 0.2, "b": 0.7}
    assert abnormality_score(state, state) == 0.0


def test_nearest_state_distance_prefers_closest_reference():
    query = {"a": 0.2, "b": 0.2}
    references = [{"a": 0.1, "b": 0.1}, {"a": 0.9, "b": 0.9}]
    assert nearest_state_distance(query, references) < 0.5


def test_rescue_improves_when_treated_moves_toward_baseline():
    baseline = {"a": 0.0, "b": 0.0}
    challenged = {"a": 1.0, "b": 1.0}
    treated = {"a": 0.25, "b": 0.25}
    assert rescue_score(baseline, challenged, treated) > 0.0


def test_audit_digest_is_reproducible():
    payload = {"x": [1, 2], "y": "abc"}
    first = build_audit_record(
        run_id="run-1",
        scenario_id="CVX-0001",
        scenario_version="0.1.0",
        model_version="model-1",
        feature_pipeline_version="features-1",
        config={"threshold": 0.5},
        seed=7,
        input_payload=payload,
    )
    second = build_audit_record(
        run_id="run-2",
        scenario_id="CVX-0001",
        scenario_version="0.1.0",
        model_version="model-1",
        feature_pipeline_version="features-1",
        config={"threshold": 0.5},
        seed=7,
        input_payload=payload,
    )
    assert first["input_digest"] == second["input_digest"]
