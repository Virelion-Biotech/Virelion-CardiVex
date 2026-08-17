import pytest

from cardivex.frozen_benchmark import build_frozen_benchmark
from cardivex.frozen_validation import run_frozen_validation


# The fixture helpers intentionally reuse the repository's existing scenario/
# calibration fixtures in the calibration and surrogate tests through imports.
from tests.test_frozen_scenario import _artifact
from tests.test_surrogate_validation import _group


def test_frozen_benchmark_is_deterministic():
    artifact = _artifact()
    specs = (("CVX-FB-1", "challenge-1"), ("CVX-FB-2", "challenge-2"))
    first = build_frozen_benchmark(
        artifact,
        condition="challenge",
        scenario_specs=specs,
        target_model="human_iPSC_derived_cardiac_tissue",
        seed=11,
    )
    second = build_frozen_benchmark(
        artifact,
        condition="challenge",
        scenario_specs=specs,
        target_model="human_iPSC_derived_cardiac_tissue",
        seed=11,
    )
    assert first.scenario_ids == second.scenario_ids
    assert [s.to_dict() for s in first.manifest.scenarios] == [s.to_dict() for s in second.manifest.scenarios]


def test_frozen_benchmark_requires_matching_artifact():
    artifact = _artifact()
    benchmark = build_frozen_benchmark(
        artifact,
        condition="challenge",
        scenario_specs=(("CVX-FB-1", "challenge-1"),),
        target_model="human_iPSC_derived_cardiac_tissue",
    )
    tampered = type(artifact)(
        dataset_id=artifact.dataset_id,
        condition_calibrations=artifact.condition_calibrations,
        translation=artifact.translation,
        development_record_ids=artifact.development_record_ids,
        held_out_group_ids=artifact.held_out_group_ids,
        excluded_record_ids=artifact.excluded_record_ids,
        source_dataset_ids=artifact.source_dataset_ids,
        artifact_id="bad-id",
    )
    with pytest.raises(ValueError, match="integrity"):
        build_frozen_benchmark(
            tampered,
            condition="challenge",
            scenario_specs=(("CVX-FB-2", "challenge-2"),),
            target_model="human_iPSC_derived_cardiac_tissue",
        )
    assert benchmark.calibration_artifact_id == artifact.artifact_id


def test_frozen_benchmark_uses_frozen_calibration_for_validation():
    artifact = _artifact()
    benchmark = build_frozen_benchmark(
        artifact,
        condition="challenge",
        scenario_specs=(("CVX-FB-1", "challenge-1"),),
        target_model="human_iPSC_derived_cardiac_tissue",
        seed=5,
    )
    groups = (_group(with_modalities=True),)
    results = __import__(
        "cardivex.frozen_benchmark", fromlist=["validate_frozen_benchmark_against_groups"]
    ).validate_frozen_benchmark_against_groups(benchmark, artifact, groups)
    assert len(results) == 1
    assert results[0].observed_dataset_ids == ("DS-SUR",)


def test_frozen_validation_rejects_empty_scenarios():
    with pytest.raises(ValueError, match="at least one scenario"):
        run_frozen_validation(_artifact(), [], (_group(),))
