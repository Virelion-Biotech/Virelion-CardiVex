import pytest

from cardivex.ingest import ingest_processed_observation
from cardivex.longitudinal import group_longitudinal_records
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.surrogate_validation import summarize_surrogate_validation, validate_scenario_against_group


def _scenario() -> Scenario:
    domains0 = {"inflammatory_activation": DomainValue(0.0, evidence_status="modeled")}
    domains1 = {"inflammatory_activation": DomainValue(0.5, evidence_status="extrapolated")}
    domains2 = {"inflammatory_activation": DomainValue(0.25, evidence_status="extrapolated")}
    return Scenario(
        scenario_id="CVX-SUR-1",
        version="0.4.0",
        name="surrogate fixture",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.MODERATE,
        phenotype_domains=domains1,
        temporal_profile=(
            ScenarioState("t0", 0.0, domains0),
            ScenarioState("t1", 1.0, domains1),
            ScenarioState("t2", 2.0, domains2),
        ),
        provenance_sources=("DS-SUR",),
        provenance_transformations=("fixture",),
        ood_status="held_out_novel",
    )


def _group():
    rows = []
    for idx, value in enumerate((0.0, 0.45, 0.2)):
        rows.append(
            ingest_processed_observation(
                observation_id=f"SUR-{idx}",
                dataset_id="DS-SUR",
                condition="challenge",
                time=float(idx),
                domain_scores={"inflammatory_activation": value},
                source_ref="fixture",
            )
        )
    rows = [
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
                metadata={**row.state.metadata, "experimental_unit_id": "UNIT-1"},
            ),
            available_modalities=row.available_modalities,
            source_ref=row.source_ref,
        )
        for row in rows
    ]
    return group_longitudinal_records(rows)[0]


def test_surrogate_validation_quantifies_holdout_error():
    result = validate_scenario_against_group(_scenario(), _group(), time_tolerance=0.0)
    assert result.acceptable
    assert result.domain_mae == pytest.approx((0.0 + 0.05 + 0.05) / 3)
    assert result.domain_max_error == pytest.approx(0.05)
    assert result.temporal_similarity > 0.9
    assert result.observed_dataset_ids == ("DS-SUR",)


def test_surrogate_summary_is_group_level():
    result = validate_scenario_against_group(_scenario(), _group())
    summary = summarize_surrogate_validation([result])
    assert summary["groups"] == 1
    assert summary["mean_domain_mae"] == pytest.approx(result.domain_mae)
