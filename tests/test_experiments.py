import pytest

from cardivex.experiments import cross_validate_centroid


def test_cross_validation_is_deterministic():
    states = [
        {"x": 0.0}, {"x": 0.1}, {"x": 0.9}, {"x": 1.0},
        {"x": 0.05}, {"x": 0.95},
    ]
    labels = ["normal", "normal", "stress", "stress", "normal", "stress"]
    first = cross_validate_centroid(states, labels, k=3)
    second = cross_validate_centroid(states, labels, k=3)
    assert first == second
    assert len(first.folds) == 3


def test_cross_validation_rejects_invalid_k():
    with pytest.raises(ValueError):
        cross_validate_centroid([{"x": 0.0}], ["a"], k=2)
