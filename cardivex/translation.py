from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .features import CardiacState, ModalityVector
from .models import Scenario


@dataclass(frozen=True)
class TranslationProfile:
    """Transparent mapping from domain scores to processed surrogate features.

    This is a benchmark abstraction: coefficients are configurable and should
    be replaced by evidence-calibrated mappings before scientific claims are made.
    """

    imaging: Mapping[str, Mapping[str, float]]
    functional: Mapping[str, Mapping[str, float]]
    omics: Mapping[str, Mapping[str, float]]


def _project(domains: Mapping[str, float], rules: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for feature, weights in rules.items():
        value = sum(float(domains.get(domain, 0.0)) * float(weight) for domain, weight in weights.items())
        result[feature] = max(0.0, min(1.0, value))
    return result


def default_translation_profile() -> TranslationProfile:
    """Return an interpretable starter mapping for synthetic benchmarking."""
    return TranslationProfile(
        imaging={
            "structural_disorganization": {"structural_disorganization": 1.0, "fibrosis_remodeling": 0.5},
            "viability_burden": {"viability_burden": 1.0, "oxidative_stress": 0.25},
            "cellular_organization": {"structural_disorganization": 0.7, "inflammatory_activation": 0.2},
        },
        functional={
            "contractile_impairment": {"contractile_impairment": 1.0, "mitochondrial_dysfunction": 0.25},
            "electrophysiologic_instability": {"electrophysiologic_disturbance": 1.0, "metabolic_stress": 0.15},
            "functional_reserve_loss": {"contractile_impairment": 0.7, "metabolic_stress": 0.3},
        },
        omics={
            "inflammatory_signature": {"inflammatory_activation": 1.0},
            "metabolic_signature": {"metabolic_stress": 0.7, "mitochondrial_dysfunction": 0.3},
            "vascular_signature": {"endothelial_vascular_dysfunction": 1.0},
            "remodeling_signature": {"fibrosis_remodeling": 1.0, "structural_disorganization": 0.2},
        },
    )


def scenario_to_multimodal(
    scenario: Scenario,
    *,
    profile: TranslationProfile | None = None,
    time: float = 0.0,
) -> CardiacState:
    """Project a scenario's domain scores into the shared multimodal contract."""
    profile = profile or default_translation_profile()
    domains = scenario.domain_vector()
    return CardiacState(
        imaging=ModalityVector("imaging", _project(domains, profile.imaging)),
        functional=ModalityVector("functional", _project(domains, profile.functional)),
        omics=ModalityVector("omics", _project(domains, profile.omics)),
        domain_scores=domains,
        time=time,
        metadata={
            "scenario_id": scenario.scenario_id,
            "scenario_version": scenario.version,
            "translation_profile": "default-v0.1.0" if profile is not None else "unknown",
        },
    )
