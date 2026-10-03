import pytest

from cardivex.ingest import ingest_processed_observation
from cardivex.translation_calibration import fit_translation_profile


def _records():
    records = []
    for i, domain_value in enumerate([0.1, 0.3, 0.6, 0.9], 1):
        records.append(
            ingest_processed_observation(
                observation_id=f"M-{i}",
                dataset_id="DS-MATCHED",
                condition="challenge",
                time=float(i),
                domain_scores={"inflammatory_activation": domain_value, "contractile_impairment": 1 - domain_value},
                imaging={"inflammatory_image": domain_value, "structural_image": domain_value * 0.5},
                functional={"contractile_signal": 1 - domain_value},
                omics={"inflammatory_signal": domain_value},
            )
        )
    return records


def test_fit_translation_profile_uses_matched_observations():
    result = fit_translation_profile(_records())
    assert result.sample_count == 4
    assert result.modality_feature_counts == {"imaging": 4, "functional": 4, "omics": 4}
    assert "inflammatory_image" in result.profile.imaging
    assert result.profile.imaging["inflammatory_image"]["inflammatory_activation"] == pytest.approx(1.0)
    assert result.profile.functional["contractile_signal"]["contractile_impairment"] == pytest.approx(1.0)


def test_translation_calibration_requires_minimum_matched_observations_before_modality_validation():
    records = _records()[:3]
    for record in records:
        assert record.state.imaging is not None
    stripped = [
        type(record)(
            observation_id=record.observation_id,
            dataset_id=record.dataset_id,
            condition=record.condition,
            time=record.time,
            state=record.state.__class__(
                imaging=None,
                functional=None,
                omics=None,
                domain_scores=record.state.domain_scores,
                time=record.state.time,
                metadata=record.state.metadata,
            ),
            available_modalities=(),
            source_ref=record.source_ref,
        )
        for record in records
    ]
    with pytest.raises(ValueError, match="matched observations"):
        fit_translation_profile(stripped)
