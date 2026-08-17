from cardivex.experiment_runner import run_centroid_experiment


def test_experiment_runner_returns_reproducible_metadata():
    states = [
        {"a": 0.0}, {"a": 0.1}, {"a": 0.9}, {"a": 1.0},
    ]
    labels = ["normal", "normal", "stress", "stress"]
    result = run_centroid_experiment(
        experiment_id="EXP-001",
        states=states,
        labels=labels,
        calibration_scores=[0.1, 0.8, 0.9, 0.2],
        calibration_labels=[0, 1, 1, 0],
        known_states=states[:2],
        held_out_scores=[0.9, 0.1],
        held_out_labels=[1, 0],
        k=2,
        seed=7,
    )
    assert result.model_record.training_sample_count == 4
    assert result.cross_validation.mean_accuracy == 1.0
    assert len(result.audit["input_digest"]) == 64


def test_experiment_runner_rejects_empty_known_states():
    try:
        run_centroid_experiment(
            experiment_id="EXP-002",
            states=[{"a": 0.0}, {"a": 1.0}],
            labels=["normal", "stress"],
            calibration_scores=[0.1, 0.9],
            calibration_labels=[0, 1],
            known_states=[],
            held_out_scores=[0.8],
            held_out_labels=[1],
            k=2,
        )
    except ValueError as exc:
        assert "known_states" in str(exc)
    else:
        raise AssertionError("expected ValueError")
