from __future__ import annotations

import pytest

from cardivex.external_validation_stats import exact_two_group_permutation, rmse_to_reference


def test_exact_two_group_permutation_exposes_small_n_floor():
    result = exact_two_group_permutation((0.0, 0.1, 0.2), (0.8, 0.9, 1.0))
    assert result.permutation_count == 20
    assert result.p_value_two_sided == pytest.approx(0.1)
    assert result.cliff_delta == pytest.approx(1.0)


def test_rmse_to_reference_is_unweighted_across_shared_domains():
    value = rmse_to_reference({"a": 0.0, "b": 1.0}, {"a": 1.0, "b": 1.0})
    assert value == pytest.approx((0.5) ** 0.5)
