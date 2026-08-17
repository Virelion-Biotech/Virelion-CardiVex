from cardivex.evaluation import best_threshold, calibration_curve, ood_evaluate


def test_calibration_selects_reasonable_threshold():
    scores = [0.05, 0.12, 0.25, 0.75, 0.85, 0.92]
    labels = [False, False, False, True, True, True]
    results = calibration_curve(scores, labels, thresholds=[0.2, 0.4, 0.6])
    best = best_threshold(results)
    assert best.balanced_accuracy == 1.0
    assert best.threshold == 0.2


def test_ood_evaluation_detects_separated_novel_states_without_self_distance():
    known = [{"a": 0.0, "b": 0.0}, {"a": 0.1, "b": 0.1}, {"a": 0.0, "b": 0.1}]
    novel = [{"a": 0.9, "b": 0.9}, {"a": 0.8, "b": 0.9}]
    result = ood_evaluate(known, novel, threshold=0.5)
    assert result.true_positive_rate == 1.0
    assert result.false_positive_rate == 0.0


def test_ood_evaluation_rejects_single_known_state_without_reference():
    try:
        ood_evaluate([{"a": 0.0}], [{"a": 1.0}], threshold=0.5)
    except ValueError as exc:
        assert "at least two known states" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_calibration_requires_both_classes():
    try:
        calibration_curve([0.1, 0.2], [True, True])
    except ValueError as exc:
        assert "both positive and negative" in str(exc)
    else:
        raise AssertionError("expected ValueError")
