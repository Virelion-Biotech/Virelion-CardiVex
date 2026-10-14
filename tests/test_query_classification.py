import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def runner(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("classification_runner", scripts / "run_improved_classification.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_query_exclusion_uses_condition_not_binary_label(runner):
    predictions = [
        {"subject_id": "donor", "condition": "normoxia", "true_label": "other", "predicted_label": "other"},
        {"subject_id": "donor", "condition": "hypoxia", "true_label": "hypoxia", "predicted_label": "other"},
        {"subject_id": "donor", "condition": "reoxygenation_1", "true_label": "other", "predicted_label": "hypoxia"},
    ]
    report = runner.query_metrics(predictions)
    assert report["excluded_reference_count"] == 1
    assert report["n_samples"] == 2
    assert report["n_subjects"] == 1
    assert report["overall_accuracy"] == 0
    assert report["macro_f1"] == 0
    assert report["observed_labels"] == ["hypoxia", "other"]


def test_query_report_does_not_invent_score_without_queries(runner):
    report = runner.query_metrics([])
    assert report["overall_accuracy"] is None
    assert report["macro_f1"] is None
    assert report["n_samples"] == 0


def test_loso_records_query_predictions_and_preserves_baseline_scores(runner):
    subjects = {
        str(i): {"normoxia": {"a": 0.2 + 0.01 * i}, "hypoxia": {"a": 0.6 + 0.01 * i},
                 "reoxygenation_1": {"a": 0.3 + 0.01 * i}, "reoxygenation_2": {"a": 0.25 + 0.01 * i}}
        for i in range(3)
    }
    report = runner.loso_centroid(subjects, feature_mode="delta", label_mode="four_class")
    assert report["overall_accuracy"] == 1
    assert len(report["predictions"]) == 12
    assert report["query_only"]["n_samples"] == 9
    assert report["query_only"]["excluded_reference_count"] == 3
    assert report["query_only"]["overall_accuracy"] == 1
    assert {p["subject_id"] for p in report["predictions"]} == set(subjects)
