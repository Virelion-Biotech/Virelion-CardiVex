from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class EvidenceTier(str, Enum):
    OBSERVED = "observed"
    CHARACTERIZED_PROXY = "characterized_proxy"
    VALIDATED_MODEL = "validated_model"
    EXTRAPOLATED = "extrapolated"


class Confidence(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    EXPLORATORY = "exploratory"


@dataclass(frozen=True)
class DomainValue:
    value: float
    uncertainty: float = 0.0
    evidence_status: str = "modeled"

    def __post_init__(self) -> None:
        for name, value in (("value", self.value), ("uncertainty", self.uncertainty)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value}")
        if self.evidence_status not in {"observed", "proxy", "modeled", "extrapolated"}:
            raise ValueError("invalid evidence_status")


@dataclass(frozen=True)
class ScenarioState:
    state: str
    relative_time: float
    domains: Mapping[str, DomainValue] = field(default_factory=dict)
    duration: float = 0.0

    def __post_init__(self) -> None:
        if self.relative_time < 0:
            raise ValueError("relative_time must be non-negative")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    version: str
    name: str
    target_model: str
    evidence_tier: EvidenceTier
    confidence: Confidence
    phenotype_domains: Mapping[str, DomainValue]
    temporal_profile: tuple[ScenarioState, ...]
    description: str = ""
    severity_profile: Mapping[str, float] = field(default_factory=dict)
    interaction_profile: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    variation_space: Mapping[str, Any] = field(default_factory=dict)
    validation_targets: tuple[str, ...] = field(default_factory=tuple)
    ood_status: str = "train"
    provenance_sources: tuple[str, ...] = field(default_factory=tuple)
    provenance_transformations: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.scenario_id.startswith("CVX-"):
            raise ValueError("scenario_id must start with CVX-")
        if len(self.temporal_profile) < 2:
            raise ValueError("temporal_profile must contain at least two states")
        if self.ood_status not in {"train", "validation", "test", "held_out_novel"}:
            raise ValueError("invalid ood_status")
        for domain, value in self.severity_profile.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"severity for {domain} must be in [0, 1]")

    def domain_vector(self) -> dict[str, float]:
        return {name: value.value for name, value in self.phenotype_domains.items()}
