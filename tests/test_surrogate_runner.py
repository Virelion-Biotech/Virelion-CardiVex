import pytest

from cardivex.ingest import ingest_processed_observation
from cardivex.longitudinal import group_longitudinal_records
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.surrogate_runner import run_surrogate_validation, surrogate_validation_json


def _scenario(sid="CVX-S1"):
    return Scenario(
        scenario_id=sid,
        version="0.4.0",
        name="fixture",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.MODERATE,
        phenotype_domains={"inflammatory_activation": DomainValue(0.4, evidence_status="extrapolated")},
        temporal_profile=(
            ScenarioState("t0", 0.0, {"inflammatory_activation": DomainValue(0.0, evidence_status="modeled")} ),
            ScenarioState("t1", 1.0, {"inflammatory_activation": DomainValue(0.4, evidence_status="extrapolated")} ),
        ),
        provenance_sources=("DS-DEV",),
        provenance_transformations=("fixture",),
        ood_status="held_out_novel",
    )


def _group(group_id, dataset_id="DS-HOLD"):
    rows = []
    for i, value in enumerate((0.0, 0.35)):
        row = ingest_processed_observation(
            observation_id=f"{group_id}-{i}",
            dataset_id=dataset_id,
            condition="challenge",
            time=float(i),
            domain_scores={"inflammatory_activation": value},
            source_ref="fixture",
        )
        rows.append(type(row)(
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
                metadata={**row.state.metadata, "experimental_unit_id": group_id},
            ),
            available_modalities=row.available_modalities,
            source_ref=row.source_ref,
        ))
    return group_longitudinal_records(rows)[0]


def test_runner_creates_clean_reproducible_result():
    run = run_surrogate_validation([_scenario()], [_group("DEV1", "DS-DEV")], [_group("H1")])
    assert run.clean_split
    assert run.scenario_count == 1
    assert run.held_out_group_count == 1
    assert len(run.results) == 1
    assert run.run_id == run_surrogate_validation([_scenario()], [_group("DEV1", "DS-DEV")], [_group("H1")]).run_id
    assert "clean_split" in surrogate_validation_json(run)


def test_runner_rejects_overlapping_units():
    with pytest.raises(ValueError, match="overlap"):
        run_surrogate_validation([_scenario()], [_group("U1", "DS-DEV")], [_group("U1", "DS-HOLD")])
