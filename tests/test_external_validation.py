from __future__ import annotations

import pytest

from cardivex.external_validation import validate_external_effect


DOMAINS = ("a", "b", "c")


def test_validate_external_effect_is_no_refit_and_reports_direction_transfer():
    result = validate_external_effect(
        {"a": 0.4, "b": 0.2, "c": 0.1},
        {"reference_transition": {"a": 0.5, "b": -0.1, "c": 0.2}},
        reference_dataset_id="reference",
        external_dataset_id="external",
    )
    assert result.domains == DOMAINS
    assert result.direction_transfer["a"].classification == "consistent"
    assert result.direction_transfer["b"].classification == "discordant"
    assert result.direction_transfer["c"].classification == "consistent"
    assert result.reference_similarity["reference_transition"].pearson_r > 0.0


def test_validate_external_effect_requires_shared_domains():
    with pytest.raises(ValueError, match="no shared domains"):
        validate_external_effect(
            {"a": 1.0},
            {"reference": {"b": 1.0}},
            reference_dataset_id="reference",
            external_dataset_id="external",
        )
