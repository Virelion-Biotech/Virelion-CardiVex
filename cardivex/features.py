from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


DOMAINS = (
    "inflammatory_activation",
    "endothelial_vascular_dysfunction",
    "metabolic_stress",
    "mitochondrial_dysfunction",
    "oxidative_stress",
    "viability_burden",
    "structural_disorganization",
    "fibrosis_remodeling",
    "contractile_impairment",
    "electrophysiologic_disturbance",
)


@dataclass(frozen=True)
class ModalityVector:
    """One modality's normalized feature representation."""

    name: str
    values: Mapping[str, float] = field(default_factory=dict)
    version: str = "0.1.0"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("modality name cannot be empty")
        for key, value in self.values.items():
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"feature '{key}' must be in [0, 1]")

    def vector(self) -> dict[str, float]:
        return {str(k): float(v) for k, v in self.values.items()}


@dataclass(frozen=True)
class CardiacState:
    """Unified multimodal state used by downstream defensive evaluation."""

    imaging: ModalityVector | None = None
    functional: ModalityVector | None = None
    omics: ModalityVector | None = None
    domain_scores: Mapping[str, float] = field(default_factory=dict)
    time: float = 0.0
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.time < 0:
            raise ValueError("time must be non-negative")
        for domain, value in self.domain_scores.items():
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"domain '{domain}' must be in [0, 1]")

    def merged_features(self) -> dict[str, float]:
        merged: dict[str, float] = {}
        for modality in (self.imaging, self.functional, self.omics):
            if modality is None:
                continue
            for key, value in modality.values.items():
                merged[f"{modality.name}:{key}"] = float(value)
        merged.update({f"domain:{k}": float(v) for k, v in self.domain_scores.items()})
        return merged


def from_domain_scores(
    scores: Mapping[str, float],
    *,
    imaging: Mapping[str, float] | None = None,
    functional: Mapping[str, float] | None = None,
    omics: Mapping[str, float] | None = None,
    time: float = 0.0,
) -> CardiacState:
    """Build a normalized multimodal state from already processed measurements.

    Adapters intentionally accept normalized downstream features, not raw
    experimental procedures. Raw-data pipelines can map into this contract.
    """
    return CardiacState(
        imaging=ModalityVector("imaging", imaging or {}) if imaging is not None else None,
        functional=ModalityVector("functional", functional or {}) if functional is not None else None,
        omics=ModalityVector("omics", omics or {}) if omics is not None else None,
        domain_scores=dict(scores),
        time=time,
    )


def scenario_to_domain_state(scenario) -> CardiacState:
    """Convert a Scenario into the common domain representation."""
    return CardiacState(
        domain_scores=scenario.domain_vector(),
        metadata={"scenario_id": scenario.scenario_id, "version": scenario.version},
    )
