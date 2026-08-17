from cardivex.benchmark import detect_state, evaluate_recovery
from cardivex.features import ModalityVector, from_domain_scores


def test_multimodal_state_merges_namespaced_features():
    state = from_domain_scores(
        {"inflammatory_activation": 0.4},
        imaging={"sarcomere_organization": 0.8},
        functional={"contractile_consistency": 0.7},
        omics={"stress_signature": 0.6},
    )
    merged = state.merged_features()
    assert merged["imaging:sarcomere_organization"] == 0.8
    assert merged["functional:contractile_consistency"] == 0.7
    assert merged["omics:stress_signature"] == 0.6


def test_detection_flags_abnormal_and_novel_state():
    result = detect_state(
        {"a": 0.0, "b": 0.0},
        {"a": 0.9, "b": 0.7},
        [{"a": 0.1, "b": 0.1}],
    )
    assert result.is_abnormal
    assert result.is_novel


def test_recovery_improves_toward_baseline():
    baseline = from_domain_scores(
        {"a": 0.0},
        imaging={"morphology": 0.0},
        functional={"contractility": 0.0},
        omics={"stress": 0.0},
    )
    challenged = from_domain_scores(
        {"a": 0.9},
        imaging={"morphology": 0.8},
        functional={"contractility": 0.9},
        omics={"stress": 0.8},
    )
    treated = from_domain_scores(
        {"a": 0.2},
        imaging={"morphology": 0.2},
        functional={"contractility": 0.3},
        omics={"stress": 0.2},
    )
    result = evaluate_recovery(baseline, challenged, treated)
    assert result.overall > 0.0
    assert result.functional > 0.0
