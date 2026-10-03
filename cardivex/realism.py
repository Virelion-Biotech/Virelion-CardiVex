from __future__ import annotations

from .models import Scenario


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def realism_score(
    scenario: Scenario,
    *,
    evidence_coverage: float,
    phenotype_agreement: float,
    temporal_agreement: float,
    functional_agreement: float,
) -> dict[str, float]:
    """Score how well a scenario is supported by available evidence.

    The output is a research-quality indicator, not a prediction of whether a
    particular real-world event will occur.
    """
    inputs = {
        "evidence_coverage": evidence_coverage,
        "phenotype_agreement": phenotype_agreement,
        "temporal_agreement": temporal_agreement,
        "functional_agreement": functional_agreement,
    }
    if any(not 0.0 <= value <= 1.0 for value in inputs.values()):
        raise ValueError("all agreement inputs must be in [0, 1]")

    evidence_penalty = 0.15 if scenario.evidence_tier.value == "extrapolated" else 0.0
    uncertainty = _mean([v.uncertainty for v in scenario.phenotype_domains.values()])
    uncertainty_penalty = 0.25 * uncertainty
    extrapolation_penalty = evidence_penalty
    base = _mean(list(inputs.values()))
    score = max(0.0, min(1.0, base - uncertainty_penalty - extrapolation_penalty))
    return {
        **inputs,
        "uncertainty_penalty": uncertainty_penalty,
        "extrapolation_penalty": extrapolation_penalty,
        "realism_score": score,
    }
