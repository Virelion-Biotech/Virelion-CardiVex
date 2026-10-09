import pytest
from cardivex.evaluation import ood_ranking_metrics


def test_perfect_reversed_and_tied_ranking():
    assert ood_ranking_metrics([0, 1], [2, 3])["auroc"] == 1
    assert ood_ranking_metrics([2, 3], [0, 1])["auroc"] == 0
    ties = ood_ranking_metrics([1, 1], [1, 1])
    assert ties["auroc"] == 0.5
    assert ties["average_precision"] == 0.5
    assert ties["independent_unit_count"] is None
    with pytest.raises(ValueError):
        ood_ranking_metrics([float("nan")], [1])
