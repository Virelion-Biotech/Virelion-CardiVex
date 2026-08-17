from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Mapping, Sequence

from .models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from .phenotypes import EmpiricalPhenotypeProfile


@dataclass(frozen=True)
class ScenarioBuildConfig:
    deviation_scale: float = 1.0
    max_delta: float = 0.25
    hold_out_novel: bool = True
    seed: int | None = 0
    use_correlation: bool = True


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _cholesky(matrix: Sequence[Sequence[float]]) -> list[list[float]] | None:
    """Return a Cholesky factor for a small correlation matrix, if PSD enough."""
    n = len(matrix)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        if len(matrix[i]) != n:
            return None
        for j in range(i + 1):
            value = float(matrix[i][j])
            if not math.isfinite(value):
                return None
            total = value - sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if total <= 1e-10:
                    return None
                lower[i][j] = math.sqrt(total)
            else:
                lower[i][j] = total / lower[j][j]
    return lower


def _correlated_z(
    rng: random.Random,
    domains: Sequence[str],
    correlation: Mapping[str, Mapping[str, float]] | None,
) -> dict[str, float]:
    independent = {domain: rng.gauss(0.0, 1.0) for domain in domains}
    if not correlation or len(domains) < 2:
        return independent
    matrix = [
        [float(correlation.get(a, {}).get(b, 1.0 if a == b else 0.0)) for b in domains]
        for a in domains
    ]
    factor = _cholesky(matrix)
    if factor is None:
        return independent
    base = [independent[d] for d in domains]
    return {
        domain: sum(factor[i][j] * base[j] for j in range(i + 1))
        for i, domain in enumerate(domains)
    }


def build_challenge_scenario(
    profile: EmpiricalPhenotypeProfile,
    *,
    scenario_id: str,
    name: str,
    target_model: str,
    config: ScenarioBuildConfig | None = None,
    correlation_matrix: Mapping[str, Mapping[str, float]] | None = None,
) -> Scenario:
    """Construct an evidence-linked downstream phenotype challenge scenario.

    When a validated empirical correlation matrix is supplied, domain deviations
    are sampled jointly rather than independently. Generated scenarios remain
    explicitly extrapolated until independently validated.
    """
    config = config or ScenarioBuildConfig()
    if not scenario_id.startswith("CVX-"):
        raise ValueError("scenario_id must start with CVX-")
    if not 0.0 <= config.max_delta <= 1.0:
        raise ValueError("max_delta must be in [0, 1]")
    if config.deviation_scale < 0:
        raise ValueError("deviation_scale must be non-negative")

    rng = random.Random(config.seed)
    domains_order = tuple(sorted(profile.domains))
    z_scores = _correlated_z(
        rng,
        domains_order,
        correlation_matrix if config.use_correlation else None,
    )
    domains: dict[str, DomainValue] = {}
    for domain in domains_order:
        stats = profile.domains[domain]
        sigma = min(config.max_delta, stats.std * config.deviation_scale)
        delta = max(-sigma, min(sigma, z_scores[domain] * sigma)) if sigma > 0 else 0.0
        value = _clip(stats.mean + delta)
        uncertainty = _clip((stats.std if stats.count > 1 else 0.2) + abs(delta) * 0.25)
        domains[domain] = DomainValue(value=value, uncertainty=uncertainty, evidence_status="extrapolated")

    baseline = ScenarioState(
        state="baseline_reference",
        relative_time=0.0,
        domains={name: DomainValue(0.0, evidence_status="modeled") for name in domains},
    )
    challenge = ScenarioState(state="challenge_state", relative_time=1.0, domains=domains)
    recovery = ScenarioState(
        state="recovery_reference",
        relative_time=2.0,
        domains={
            name: DomainValue(value.value * 0.5, uncertainty=value.uncertainty, evidence_status="extrapolated")
            for name, value in domains.items()
        },
    )
    transformations = [
        "empirical_profile_fit",
        f"bounded_sampling(seed={config.seed},scale={config.deviation_scale},max_delta={config.max_delta})",
    ]
    if correlation_matrix and config.use_correlation:
        transformations.append("correlation_aware_sampling")
    else:
        transformations.append("independent_sampling_fallback")
    return Scenario(
        scenario_id=scenario_id,
        version="0.3.0",
        name=name,
        description="Evidence-linked phenotype challenge generated from an empirical downstream-state profile.",
        target_model=target_model,
        evidence_tier=EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.MODERATE if profile.sample_count >= 5 else Confidence.EXPLORATORY,
        phenotype_domains=domains,
        temporal_profile=(baseline, challenge, recovery),
        severity_profile={"challenge": max((v.value for v in domains.values()), default=0.0)},
        variation_space={
            "enabled": True,
            "max_deviation": config.max_delta,
            "allowed_domains": sorted(domains),
            "correlation_aware": bool(correlation_matrix and config.use_correlation),
        },
        validation_targets=("domain_profile_agreement", "multimodal_state_consistency", "temporal_response_consistency"),
        ood_status="held_out_novel" if config.hold_out_novel else "test",
        provenance_sources=tuple(profile.source_dataset_ids),
        provenance_transformations=tuple(transformations),
    )


def compose_novel_profile(
    profiles: Mapping[str, EmpiricalPhenotypeProfile],
    *,
    weights: Mapping[str, float],
) -> dict[str, float]:
    """Create a bounded new combination of domain means from known profiles."""
    if not weights:
        raise ValueError("weights cannot be empty")
    unknown = set(weights) - set(profiles)
    if unknown:
        raise KeyError(f"unknown profiles: {sorted(unknown)}")
    total = sum(float(v) for v in weights.values())
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    normalized = {key: float(value) / total for key, value in weights.items()}
    domains = set().union(*(profiles[key].domains for key in normalized))
    result: dict[str, float] = {}
    for domain in domains:
        value = sum(
            normalized[key] * (profiles[key].domains[domain].mean if domain in profiles[key].domains else 0.0)
            for key in normalized
        )
        result[domain] = _clip(value)
    return result
