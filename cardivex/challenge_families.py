from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .models import Scenario
from .novelty import novelty_margin
from .scenario_builder import ScenarioBuildConfig, build_challenge_scenario, compose_novel_profile
from .trajectory import bounded_trajectory, shift_timeline
from .phenotypes import EmpiricalPhenotypeProfile


@dataclass(frozen=True)
class ChallengeFamily:
    name: str
    description: str
    scenario_type: str


FAMILIES: tuple[ChallengeFamily, ...] = (
    ChallengeFamily("familiar", "Evidence-linked challenge represented in the reference library.", "familiar"),
    ChallengeFamily("severity_shift", "Known phenotype with bounded severity variation.", "severity_shift"),
    ChallengeFamily("temporal_shift", "Known phenotype with a bounded temporal trajectory shift.", "temporal_shift"),
    ChallengeFamily("combinatorial", "New combination of individually characterized phenotype domains.", "combinatorial"),
    ChallengeFamily("held_out_novel", "Challenge withheld from model development to test unknown-state detection.", "held_out_novel"),
)


def build_severity_shift(
    profile: EmpiricalPhenotypeProfile,
    *,
    scenario_id: str,
    scale: float,
    seed: int | None = 0,
) -> Scenario:
    if not 0.0 <= scale <= 1.5:
        raise ValueError("scale must be in [0, 1.5]")
    scaled = EmpiricalPhenotypeProfile(
        condition=profile.condition,
        domains={
            name: type(stats)(
                mean=max(0.0, min(1.0, stats.mean * scale)),
                std=stats.std,
                minimum=max(0.0, min(1.0, stats.minimum * scale)),
                maximum=max(0.0, min(1.0, stats.maximum * scale)),
                count=stats.count,
            )
            for name, stats in profile.domains.items()
        },
        sample_count=profile.sample_count,
        source_dataset_ids=profile.source_dataset_ids,
        feature_contract=profile.feature_contract,
    )
    return build_challenge_scenario(
        scaled,
        scenario_id=scenario_id,
        name=f"Severity-shift {scale:.2f}",
        target_model="human_iPSC_derived_cardiac_tissue",
        config=ScenarioBuildConfig(seed=seed, hold_out_novel=True),
    )


def build_temporal_shift(
    scenario: Scenario,
    *,
    scenario_id: str,
    time_scale: float,
) -> Scenario:
    if time_scale <= 0:
        raise ValueError("time_scale must be positive")
    shifted = shift_timeline(tuple(scenario.temporal_profile), scale=time_scale)
    return type(scenario)(
        scenario_id=scenario_id,
        version="0.3.0",
        name=f"{scenario.name} temporal shift {time_scale:.2f}",
        target_model=scenario.target_model,
        evidence_tier=scenario.evidence_tier,
        confidence=scenario.confidence,
        phenotype_domains=scenario.phenotype_domains,
        temporal_profile=shifted,
        description=scenario.description,
        severity_profile=scenario.severity_profile,
        interaction_profile=scenario.interaction_profile,
        variation_space=scenario.variation_space,
        validation_targets=scenario.validation_targets,
        ood_status="held_out_novel",
        provenance_sources=scenario.provenance_sources,
        provenance_transformations=scenario.provenance_transformations + (f"temporal_shift(scale={time_scale})",),
    )


def build_combinatorial(
    profiles: Mapping[str, EmpiricalPhenotypeProfile],
    *,
    weights: Mapping[str, float],
    scenario_id: str,
) -> Scenario:
    domain_means = compose_novel_profile(profiles, weights=weights)
    trajectory = bounded_trajectory(domain_means, recovery_fraction=0.5)
    sources = tuple(sorted({source for key in weights for source in profiles[key].source_dataset_ids}))
    return Scenario(
        scenario_id=scenario_id,
        version="0.3.0",
        name="Combinatorial phenotype challenge",
        target_model="human_iPSC_derived_cardiac_tissue",
        evidence_tier=__import__("cardivex.models", fromlist=["EvidenceTier"]).EvidenceTier.EXTRAPOLATED,
        confidence=__import__("cardivex.models", fromlist=["Confidence"]).Confidence.EXPLORATORY,
        phenotype_domains={
            name: __import__("cardivex.models", fromlist=["DomainValue"]).DomainValue(value=value, uncertainty=0.25, evidence_status="extrapolated")
            for name, value in domain_means.items()
        },
        temporal_profile=trajectory,
        description="A bounded new combination of previously characterized downstream phenotype profiles.",
        severity_profile={"challenge": max(domain_means.values(), default=0.0)},
        variation_space={"enabled": False},
        validation_targets=("held_out_multimodal_measurements", "domain_profile_agreement"),
        ood_status="held_out_novel",
        provenance_sources=sources,
        provenance_transformations=(f"weighted_profile_composition(weights={dict(weights)})",),
    )


def family_is_novel(scenario: Scenario, known: Sequence[Scenario], *, threshold: float = 0.35) -> bool:
    known_vectors = [item.domain_vector() for item in known]
    return novelty_margin(scenario.domain_vector(), known_vectors) >= threshold if known_vectors else True
