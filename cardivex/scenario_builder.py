from __future__ import annotations

from dataclasses import replace
import random
from typing import Mapping

from .models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from .phenotypes import EmpiricalPhenotypeProfile


@dataclass(frozen=True)
class ScenarioBuildConfig:
    deviation_scale: float = 1.0
    max_delta: float = 0.25
    hold_out_novel: bool = True
    seed: int | None = 0


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def build_challenge_scenario(
    profile: EmpiricalPhenotypeProfile,
    *,
    scenario_id: str,
    name: str,
    target_model: str,
    config: ScenarioBuildConfig | None = None,
) -> Scenario:
    """Construct an evidence-linked phenotype scenario from an empirical profile.

    This operates only on measured downstream phenotype distributions. It does
    not represent initiating-agent construction, optimization, or deployment.
    """
    config = config or ScenarioBuildConfig()
    if not scenario_id.startswith("CVX-"):
        raise ValueError("scenario_id must start with CVX-")
    if config.max_delta < 0 or config.max_delta > 1:
        raise ValueError("max_delta must be in [0, 1]")
    rng = random.Random(config.seed)
    domains: dict[str, DomainValue] = {}
    for domain, stats in profile.domains.items():
        sigma = min(config.max_delta, stats.std * config.deviation_scale)
        delta = rng.uniform(-sigma, sigma) if sigma > 0 else 0.0
        value = _clip(stats.mean + delta)
        uncertainty = _clip((stats.std if stats.count > 1 else 0.2) + abs(delta) * 0.25)
        domains[domain] = DomainValue(value=value, uncertainty=uncertainty, evidence_status="modeled")

    baseline = ScenarioState(
        state="baseline_reference",
        relative_time=0.0,
        domains={name: DomainValue(0.0, evidence_status="modeled") for name in domains},
    )
    challenge = ScenarioState(
        state="challenge_state",
        relative_time=1.0,
        domains=domains,
    )
    recovery = ScenarioState(
        state="recovery_reference",
        relative_time=2.0,
        domains={name: DomainValue(value.value * 0.5, uncertainty=value.uncertainty, evidence_status="modeled") for name, value in domains.items()},
    )
    return Scenario(
        scenario_id=scenario_id,
        version="0.2.0",
        name=name,
        description="Evidence-linked phenotype challenge generated from an empirical downstream-state profile.",
        target_model=target_model,
        evidence_tier=EvidenceTier.VALIDATED_MODEL if profile.sample_count >= 5 else EvidenceTier.EXTRAPOLATED,
        confidence=Confidence.MODERATE if profile.sample_count >= 5 else Confidence.EXPLORATORY,
        phenotype_domains=domains,
        temporal_profile=(baseline, challenge, recovery),
        severity_profile={"challenge": max((v.value for v in domains.values()), default=0.0)},
        variation_space={"enabled": True, "max_deviation": config.max_delta, "allowed_domains": sorted(domains)},
        validation_targets=("domain_profile_agreement", "multimodal_state_consistency", "temporal_response_consistency"),
        ood_status="held_out_novel" if config.hold_out_novel else "test",
        provenance_sources=tuple(profile.source_dataset_ids),
        provenance_transformations=(
            "empirical_profile_fit",
            f"bounded_sampling(seed={config.seed},scale={config.deviation_scale},max_delta={config.max_delta})",
        ),
    )


def compose_novel_profile(
    profiles: Mapping[str, EmpiricalPhenotypeProfile],
    *,
    weights: Mapping[str, float],
) -> dict[str, float]:
    """Create a bounded new combination of domain means from known profiles."""
    if not weights:
        raise ValueError("weights cannot be empty")
    total = sum(float(v) for v in weights.values())
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    normalized = {key: float(value) / total for key, value in weights.items()}
    domains = set().union(*(profiles[key].domains for key in normalized))
    return {
        domain: _clip(sum(normalized[key] * profiles[key].domains.get(domain, type("S", (), {"mean": 0.0})) .mean for key in normalized))
        for domain in domains
    }
