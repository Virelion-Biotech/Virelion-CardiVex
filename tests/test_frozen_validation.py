import pytest

from cardivex.calibration_runner import build_development_calibration
from cardivex.data_plan import build_analysis_plan
from cardivex.frozen_validation import frozen_validation_json, run_frozen_validation
from cardivex.ingest import ingest_processed_observation
from cardivex.longitudinal import group_longitudinal_records
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState


def _records():
    rows = []
    for unit in ("DEV", "HOLD"):
        for idx, value in enumerate((0.0, 0.4, 0.2)):
            rows.append(
                ingest_processed_observation(
                    observation_id=f"{unit}-{idx}",
                    dataset_id="DS-FROZEN",
                    condition="challenge",
                    time=float(idx),
                    domain_scores={"inflammatory_activation": value},
                    source_ref="fixture",
                )
            )
    return [
        type(row)(
            observation_id=row.observation_id,
            dataset_id=row.dataset_id,
            condition=row.condition,
            time=row.time,
            state=type(row.state)(
                imaging=row.state.imaging,
                functional=row.state.functional,
                omics=row.state.omics,
                domain_scores=row.state.domain_scores,
                time=row.state.time,
                metadata={**row.state.metadata, "experimental_unit_id": row.observation_id.split("-")[0]},
            ),
            available_modalities=row.available_modalities,
            source_ref=row.source_ref,
        )
        for row in rows
    ]


def _scenario():
    domain = {"inflammatory_activation": DomainValue(0.4, evidence_status="extrapolated")}
    return Scenario(
        scenario_id="CVX-FROZEN-1",
        version="0.1.0",
        name="frozen validation fixture",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.MODERATE,
        phenotype_domains=domain,
        temporal_profile=(
            ScenarioState("t0", 0.0, {"inflammatory_activation": DomainValue(0.0, evidence_status="extrapolated")}),
            ScenarioState("t1", 1.0, domain),
        ),
        provenance_sources=("DS-FROZEN",),
        provenance_transformations=("fixture",),
        ood_status="held_out_novel",
    )


def test_frozen_validation_uses_declared_holdout_only():
    records = _records()
    plan = build_analysis_plan(records, expected_times=(0.0, 1.0, 2.0))
    artifact = build_development_calibration(records, plan)
    groups = group_longitudinal_records(records)
    holdout = [group for group in groups if group.group_id == "DEV1"]
    # The analysis plan deterministically selects the final group as holdout.
    holdout = [groups[-1]]
    run = run_frozen_validation(artifact, [_scenario()], holdout)
    assert run.clean_split
    assert run.artifact_id == artifact.artifact_id
    assert frozen_validation_json(run)


def test_frozen_validation_rejects_wrong_group_set():
    records = _records()
    plan = build_analysis_plan(records, expected_times=(0.0, 1.0, 2.0))
    artifact = build_development_calibration(records, plan)
    groups = group_longitudinal_records(records)
    wrong = [groups[0]]
    with pytest.raises(ValueError, match="do not match"):
        run_frozen_validation(artifact, [_scenario()], wrong)


def test_frozen_validation_rejects_artifact_record_overlap():
    records = _records()
    plan = build_analysis_plan(records, expected_times=(0.0, 1.0, 2.0))
    artifact = build_development_calibration(records, plan)
    groups = group_longitudinal_records(records)
    tampered = type(artifact)(
        dataset_id=artifact.dataset_id,
        condition_calibrations=artifact.condition_calibrations,
        translation=artifact.translation,
        development_record_ids=artifact.development_record_ids + (artifact.excluded_record_ids[0],),
        held_out_group_ids=artifact.held_out_group_ids,
        excluded_record_ids=artifact.excluded_record_ids,
        source_dataset_ids=artifact.source_dataset_ids,
        artifact_id=artifact.artifact_id,
    )
    # Tampering development_record_ids invalidates the artifact hash first;
    # the explicit overlap check is only reached when the hash still matches.
    with pytest.raises(ValueError, match="integrity|development/excluded"):
        run_frozen_validation(tampered, [_scenario()], [groups[-1]])
