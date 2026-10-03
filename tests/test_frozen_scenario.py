import pytest

from cardivex.calibration_runner import CalibrationArtifact
from cardivex.frozen_scenario import build_scenario_from_frozen_calibration
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.phenotypes import DomainDistribution, EmpiricalPhenotypeProfile
from cardivex.temporal import EmpiricalTemporalProfile, TemporalPoint


def _artifact() -> CalibrationArtifact:
    profile = EmpiricalPhenotypeProfile(
        condition="challenge",
        domains={
            "inflammatory_activation": DomainDistribution(0.4, 0.1, 0.2, 0.6, 4),
            "contractile_impairment": DomainDistribution(0.3, 0.05, 0.2, 0.4, 4),
        },
        sample_count=4,
        source_dataset_ids=("DS-FROZEN",),
    )
    temporal = EmpiricalTemporalProfile(
        condition="challenge",
        points=(
            TemporalPoint(0.0, {"inflammatory_activation": DomainValue(0.1)}, 2),
            TemporalPoint(1.0, {"inflammatory_activation": DomainValue(0.4)}, 2),
        ),
        source_dataset_ids=("DS-FROZEN",),
    )
    from cardivex.calibration_runner import ConditionCalibration, compute_artifact_id

    artifact = CalibrationArtifact(
        dataset_id="DS-FROZEN",
        condition_calibrations=(ConditionCalibration("challenge", profile, {
            "inflammatory_activation": {"inflammatory_activation": 1.0, "contractile_impairment": 0.2},
            "contractile_impairment": {"inflammatory_activation": 0.2, "contractile_impairment": 1.0},
        }, temporal),),
        translation=None,
        development_record_ids=("DEV-1", "DEV-2"),
        held_out_group_ids=("HOLDOUT-1",),
        excluded_record_ids=("H-1",),
        source_dataset_ids=("DS-FROZEN",),
        artifact_id="",
    )
    return CalibrationArtifact(**{**artifact.__dict__, "artifact_id": compute_artifact_id(artifact)})


def test_generation_is_bound_to_frozen_artifact():
    artifact = _artifact()
    scenario = build_scenario_from_frozen_calibration(
        artifact,
        condition="challenge",
        scenario_id="CVX-FROZEN-1",
        name="frozen fixture",
        target_model="human_iPSC_derived_cardiac_tissue",
    )
    assert f"frozen_calibration:{artifact.artifact_id}" in scenario.provenance_transformations
    assert scenario.variation_space["frozen_calibration_artifact"] == artifact.artifact_id
    assert scenario.evidence_tier == EvidenceTier.EXTRAPOLATED


def test_tampered_artifact_is_rejected():
    artifact = _artifact()
    broken = CalibrationArtifact(**{**artifact.__dict__, "artifact_id": "0000000000000000"})
    with pytest.raises(ValueError, match="integrity"):
        build_scenario_from_frozen_calibration(
            broken,
            condition="challenge",
            scenario_id="CVX-FROZEN-2",
            name="broken",
            target_model="human_iPSC_derived_cardiac_tissue",
        )


def test_unknown_condition_is_rejected():
    with pytest.raises(ValueError, match="condition"):
        build_scenario_from_frozen_calibration(
            _artifact(),
            condition="missing",
            scenario_id="CVX-FROZEN-3",
            name="missing",
            target_model="human_iPSC_derived_cardiac_tissue",
        )
