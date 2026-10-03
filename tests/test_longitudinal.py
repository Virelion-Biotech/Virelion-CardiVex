import pytest

from cardivex.ingest import ingest_processed_observation
from cardivex.longitudinal import (
    align_to_time_grid,
    group_longitudinal_records,
    longitudinal_domain_series,
    longitudinal_feature_series,
    validate_longitudinal_group,
)


def record(obs, unit, time, condition="challenge", modalities=False):
    return ingest_processed_observation(
        observation_id=obs,
        dataset_id="DS-LONG",
        condition=condition,
        time=time,
        domain_scores={"inflammatory_activation": 0.2 + 0.1 * time},
        imaging={"viability_burden": 0.1} if modalities else None,
        source_ref=f"unit={unit}",
    )


def test_grouping_requires_explicit_unit_metadata():
    rec = record("O1", "U1", 0.0)
    with pytest.raises(ValueError, match="experimental_unit_id"):
        group_longitudinal_records([rec])


def test_grouping_and_validation_with_unit_metadata():
    rows = [record("O1", "U1", 0.0, modalities=True), record("O2", "U1", 1.0, modalities=True)]
    rows = [
        type(r)(
            observation_id=r.observation_id,
            dataset_id=r.dataset_id,
            condition=r.condition,
            time=r.time,
            state=type(r.state)(
                imaging=r.state.imaging,
                functional=r.state.functional,
                omics=r.state.omics,
                domain_scores=r.state.domain_scores,
                time=r.state.time,
                metadata={**r.state.metadata, "experimental_unit_id": "U1"},
            ),
            available_modalities=r.available_modalities,
            source_ref=r.source_ref,
        )
        for r in rows
    ]
    groups = group_longitudinal_records(rows)
    assert len(groups) == 1
    validation = validate_longitudinal_group(groups[0], expected_times=[0.0, 1.0], required_modalities=["imaging"])
    assert validation.valid is True
    assert validation.point_count == 2


def test_duplicate_and_missing_time_points_are_flagged():
    rows = []
    for obs, time in [("O1", 0.0), ("O2", 0.0), ("O3", 2.0)]:
        r = record(obs, "U2", time)
        r = type(r)(
            observation_id=r.observation_id,
            dataset_id=r.dataset_id,
            condition=r.condition,
            time=r.time,
            state=type(r.state)(
                imaging=r.state.imaging,
                functional=r.state.functional,
                omics=r.state.omics,
                domain_scores=r.state.domain_scores,
                time=r.state.time,
                metadata={**r.state.metadata, "experimental_unit_id": "U2"},
            ),
            available_modalities=r.available_modalities,
            source_ref=r.source_ref,
        )
        rows.append(r)
    group = group_longitudinal_records(rows)[0]
    validation = validate_longitudinal_group(group, expected_times=[0.0, 1.0, 2.0])
    assert validation.valid is False
    assert validation.duplicate_times == (0.0,)
    assert validation.missing_time_points == (1.0,)


def test_time_grid_alignment_is_nonduplicating():
    rows = [record("O1", "U3", 0.0), record("O2", "U3", 1.05), record("O3", "U3", 2.1)]
    aligned = align_to_time_grid(rows, target_times=[0.0, 1.0, 2.0], tolerance=0.1)
    assert set(aligned) == {0.0, 1.0}
    assert len({r.observation_id for r in aligned.values()}) == 2


def test_longitudinal_series_preserve_observed_values_only():
    rows = [record("O1", "U4", 0.0, modalities=True), record("O2", "U4", 1.0, modalities=True)]
    rows = [
        type(r)(
            observation_id=r.observation_id,
            dataset_id=r.dataset_id,
            condition=r.condition,
            time=r.time,
            state=type(r.state)(
                imaging=r.state.imaging,
                functional=r.state.functional,
                omics=r.state.omics,
                domain_scores=r.state.domain_scores,
                time=r.state.time,
                metadata={**r.state.metadata, "experimental_unit_id": "U4"},
            ),
            available_modalities=r.available_modalities,
            source_ref=r.source_ref,
        )
        for r in rows
    ]
    group = group_longitudinal_records(rows)[0]
    series = longitudinal_domain_series(group)
    features = longitudinal_feature_series(group)
    assert len(series["inflammatory_activation"]) == 2
    assert set(features["imaging"]) == {0.0, 1.0}
