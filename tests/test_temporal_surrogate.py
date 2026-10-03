import pytest

from cardivex.ingest import ingest_processed_observation
from cardivex.longitudinal import group_longitudinal_records
from cardivex.temporal_surrogate import (
    TemporalSurrogateSpec,
    evaluate_temporal_surrogate,
    fit_temporal_surrogate,
)


def _group(group_id: str, values: tuple[float, ...]):
    records = []
    for index, value in enumerate(values):
        records.append(
            ingest_processed_observation(
                observation_id=f"{group_id}-{index}",
                dataset_id="TEST",
                condition="challenge",
                time=float(index),
                domain_scores={"stress": value, "contractile": max(0.0, 1.0 - value)},
                omics={"dummy": value},
                source_ref="fixture",
            )
        )
        records[-1] = records[-1].__class__(
            observation_id=records[-1].observation_id,
            dataset_id=records[-1].dataset_id,
            condition=records[-1].condition,
            time=records[-1].time,
            state=records[-1].state.__class__(
                imaging=records[-1].state.imaging,
                functional=records[-1].state.functional,
                omics=records[-1].state.omics,
                domain_scores=records[-1].state.domain_scores,
                time=records[-1].state.time,
                metadata={**records[-1].state.metadata, "experimental_unit_id": group_id},
            ),
            available_modalities=records[-1].available_modalities,
            source_ref=records[-1].source_ref,
        )
    return group_longitudinal_records(records)


def test_temporal_surrogate_learns_transition():
    development = _group("DEV", (0.1, 0.2, 0.3))
    model = fit_temporal_surrogate(development, spec=TemporalSurrogateSpec(epochs=300, learning_rate=0.05))
    prediction = model.predict_next({"stress": 0.2, "contractile": 0.8}, delta=1.0)
    assert 0.0 <= prediction["stress"] <= 1.0
    assert prediction["stress"] > 0.1


def test_temporal_surrogate_rejects_overlap():
    development = _group("SAME", (0.1, 0.2, 0.3))
    held_out = _group("SAME", (0.2, 0.3, 0.4))
    model = fit_temporal_surrogate(development)
    with pytest.raises(ValueError, match="overlap"):
        evaluate_temporal_surrogate(model, held_out, development_groups=development)


def test_temporal_surrogate_reports_held_out_error():
    development = _group("DEV", (0.1, 0.2, 0.3))
    held_out = _group("TEST", (0.2, 0.3, 0.4))
    model = fit_temporal_surrogate(development)
    report = evaluate_temporal_surrogate(model, held_out, development_groups=development)
    assert report["transition_count"] == 2.0
    assert report["mean_absolute_error"] >= 0.0
