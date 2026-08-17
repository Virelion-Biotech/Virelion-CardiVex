from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

from .models import Scenario


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"


def validate_scenario(scenario: Scenario) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    times = [state.relative_time for state in scenario.temporal_profile]
    if times != sorted(times) or len(set(times)) != len(times):
        issues.append(ValidationIssue("NON_MONOTONIC_TIME", "temporal_profile times must be strictly increasing"))

    if not scenario.provenance_sources:
        issues.append(ValidationIssue("MISSING_PROVENANCE", "scenario has no provenance sources"))
    if not scenario.provenance_transformations:
        issues.append(ValidationIssue("MISSING_TRANSFORM_TRACE", "scenario has no transformation lineage"))

    if scenario.evidence_tier.value == "extrapolated" and scenario.confidence.value == "high":
        issues.append(ValidationIssue("OVERCONFIDENT_EXTRAPOLATION", "extrapolated scenarios cannot be marked high confidence"))

    if scenario.ood_status == "held_out_novel" and not scenario.provenance_transformations:
        issues.append(ValidationIssue("MISSING_NOVELTY_TRACE", "held-out novel scenario needs an explicit transformation lineage"))

    if scenario.evidence_tier.value == "observed":
        for name, value in scenario.phenotype_domains.items():
            if value.evidence_status not in {"observed", "proxy"}:
                issues.append(ValidationIssue("OBSERVED_STATUS_MISMATCH", f"{name} is not marked observed/proxy in an observed scenario"))

    for state in scenario.temporal_profile:
        for name, value in state.domains.items():
            if not isfinite(value.value) or not isfinite(value.uncertainty):
                issues.append(ValidationIssue("NONFINITE_DOMAIN_VALUE", f"{scenario.scenario_id}:{name} contains non-finite data"))

    return issues


def detect_direct_leakage(
    train_scenarios: Iterable[Scenario],
    held_out_scenarios: Iterable[Scenario],
) -> list[ValidationIssue]:
    """Detect exact scenario/domain-vector duplication across benchmark splits."""
    train = tuple(train_scenarios)
    held_out = tuple(held_out_scenarios)
    train_ids = {s.scenario_id for s in train}
    train_vectors = {tuple(sorted(s.domain_vector().items())) for s in train}
    issues: list[ValidationIssue] = []
    for scenario in held_out:
        if scenario.scenario_id in train_ids:
            issues.append(ValidationIssue("SCENARIO_ID_LEAK", f"{scenario.scenario_id} appears in training data"))
        if tuple(sorted(scenario.domain_vector().items())) in train_vectors:
            issues.append(ValidationIssue("VECTOR_LEAK", f"{scenario.scenario_id} exactly matches a training phenotype vector"))
    return issues
