import pytest

from cardivex.temporal_metrics import temporal_shift_error, trajectory_error


def test_trajectory_error_and_similarity():
    predicted = {
        "a": ((0.0, 0.1), (1.0, 0.5), (2.0, 0.7)),
        "b": ((0.0, 0.2), (1.0, 0.4), (2.0, 0.6)),
    }
    observed = {
        "a": ((0.0, 0.2), (1.0, 0.4), (2.0, 0.8)),
        "b": ((0.0, 0.2), (1.0, 0.5), (2.0, 0.5)),
    }
    result = trajectory_error(predicted, observed)
    assert result.point_count == 6
    assert result.domain_count == 2
    assert result.mae == pytest.approx((0.1 + 0.1 + 0.1 + 0.0 + 0.1 + 0.1) / 6)
    assert 0.0 <= result.similarity <= 1.0


def test_temporal_shift_error_requires_shared_points():
    with pytest.raises(ValueError):
        temporal_shift_error({"a": ((0.0, 0.1),)}, {"a": ((1.0, 0.1),)})
