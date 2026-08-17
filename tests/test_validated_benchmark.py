import pytest

from cardivex.features import from_domain_scores
from cardivex.ingest import ingest_processed_observation
from cardivex.longitudinal import group_longitudinal_records
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.validated_benchmark import run_validated_benchmark, validated_benchmark_json


def _scenario(sid: str, value: float, status: str) -> Scenario:
    domain = {"inflammatory_activation": DomainValue(value, evidence_status="extrapolated")}
    return Scenario(
        scenario_id=sid,
        version="0.4.0",
        name="validated benchmark fixture",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.EXPLORATORY,
        phenotype_domains=domain,
        temporal_profile=(
            ScenarioState("t0", 0.0, {"inflammatory_activation": DomainValue(0.0)}),
            ScenarioState("t1", 1.0, domain),
        ),
        provenance_sources=("DS-DEV",),
        provenance_transformations=("fixture",),
        ood_status=status,
    )


def _group(group_id: str, dataset_id: str):
    rows = []
    for idx, value in enumerate((0.0, 0.35)):
        row = ingest_processed_observation(
            observation_id=f"{group_id}-{idx}",
            dataset_id=dataset_id,
            condition="challenge",
            time=float(idx),
            domain_scores={"inflammatory_activation": value},
            imaging={"inflammatory_signal": value},
            functional={"contractile_signal": 1.0 - value},
            omics={"inflammatory_signature": value},
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


def test_validated_benchmark_combines_benchmark_and_surrogate_layers():
    scenarios = (
        _scenario("CVX-9200", 0.2, "train"),
        _scenario("CVX-9201", 0.95, "held_out_novel"),
    )
    baseline = from_domain_scores({"inflammatory_activation": 0.0})
    run = run_validated_benchmark(
        scenarios,
        baseline=baseline,
        known_states=[baseline],
        development_groups=[_group("DEV-1", "DS-DEV")],
        held_out_groups=[_group("HOLD-1", "DS-HOLD")],
    )
    assert run.surrogate_validation.clean_split
    assert len(run.surrogate_validation.results) == 2
    assert run.validation_policy["held_out_units_disjoint"] is True
    assert "surrogate_validation" in validated_benchmark_json(run)


def test_validated_benchmark_rejects_unit_overlap():
    baseline = from_domain_scores({"inflammatory_activation": 0.0})
    with pytest.raises(ValueError, match="overlap"):
        run_validated_benchmark(
            [_scenario("CVX-9202", 0.5, "held_out_novel")],
            baseline=baseline,
            known_states=[baseline],
            development_groups=[_group("U-1", "DS-DEV")],
            held_out_groups=[_group("U-1", "DS-HOLD")],
        )
