from cardivex.ingest import ingest_processed_observation
from cardivex.longitudinal import group_longitudinal_records
from cardivex.temporal_benchmark import benchmark_temporal_surrogate
from cardivex.temporal_surrogate import TemporalSurrogateSpec, fit_temporal_surrogate


def _group(group_id: str, values: tuple[float, ...]):
    records = []
    for index, value in enumerate(values):
        record = ingest_processed_observation(
            observation_id=f"{group_id}-{index}",
            dataset_id="TEST",
            condition="challenge",
            time=float(index),
            domain_scores={"stress": value, "contractile": max(0.0, 1.0 - value)},
            omics={"dummy": value},
            source_ref="fixture",
        )
        state = record.state.__class__(
            imaging=record.state.imaging,
            functional=record.state.functional,
            omics=record.state.omics,
            domain_scores=record.state.domain_scores,
            time=record.state.time,
            metadata={**record.state.metadata, "experimental_unit_id": group_id},
        )
        records.append(record.__class__(
            observation_id=record.observation_id,
            dataset_id=record.dataset_id,
            condition=record.condition,
            time=record.time,
            state=state,
            available_modalities=record.available_modalities,
            source_ref=record.source_ref,
        ))
    return group_longitudinal_records(records)


def test_temporal_benchmark_reports_persistence_reference():
    development = _group("DEV", (0.1, 0.2, 0.3, 0.4))
    held_out = _group("TEST", (0.2, 0.3, 0.4, 0.5))
    model = fit_temporal_surrogate(
        development,
        spec=TemporalSurrogateSpec(epochs=400, learning_rate=0.05),
    )
    report = benchmark_temporal_surrogate(model, held_out, development_groups=development)
    assert report.transition_count == 3
    assert report.evaluated_domain_values == 6
    assert report.persistence_mean_absolute_error > 0.0
    assert report.model_mean_absolute_error >= 0.0
    assert -1.0 < report.improvement_vs_persistence < 1.0


def test_temporal_benchmark_rejects_leakage():
    development = _group("SAME", (0.1, 0.2, 0.3))
    held_out = _group("SAME", (0.2, 0.3, 0.4))
    model = fit_temporal_surrogate(development)
    try:
        benchmark_temporal_surrogate(model, held_out, development_groups=development)
    except ValueError as exc:
        assert "overlap" in str(exc)
    else:
        raise AssertionError("overlapping development and held-out groups must be rejected")
