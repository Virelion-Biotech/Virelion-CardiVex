from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from statistics import mean
from typing import Mapping, Sequence


@dataclass(frozen=True)
class DirectionTransfer:
    """No-refit comparison of one external effect against frozen reference effects."""

    external_effect: float
    reference_effects: Mapping[str, float]
    sign_agreement_fraction: float
    classification: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceSimilarity:
    """Scale-free similarity between two domain-effect vectors."""

    pearson_r: float
    cosine_similarity: float


@dataclass(frozen=True)
class ExternalValidationResult:
    """Frozen-reference external validation in a shared module representation.

    This intentionally operates on effect vectors rather than refitting a
    scaler or predictive model on the external dataset.
    """

    reference_dataset_id: str
    external_dataset_id: str
    domains: tuple[str, ...]
    external_effect: Mapping[str, float]
    direction_transfer: Mapping[str, DirectionTransfer]
    reference_similarity: Mapping[str, ReferenceSimilarity]
    overall_effect_l1: float
    overall_effect_l2: float

    def to_dict(self) -> dict[str, object]:
        return {
            "reference_dataset_id": self.reference_dataset_id,
            "external_dataset_id": self.external_dataset_id,
            "domains": self.domains,
            "external_effect": dict(self.external_effect),
            "direction_transfer": {
                domain: result.to_dict() for domain, result in self.direction_transfer.items()
            },
            "reference_similarity": {
                name: asdict(result) for name, result in self.reference_similarity.items()
            },
            "overall_effect_l1": self.overall_effect_l1,
            "overall_effect_l2": self.overall_effect_l2,
        }


def _shared_domains(*vectors: Mapping[str, float]) -> tuple[str, ...]:
    if not vectors:
        raise ValueError("at least one vector is required")
    shared = set(vectors[0])
    for vector in vectors[1:]:
        shared &= set(vector)
    if not shared:
        raise ValueError("vectors have no shared domains")
    return tuple(sorted(shared))


def _pearson(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        raise ValueError("Pearson correlation requires equal vectors with at least two values")
    a_mean = mean(a)
    b_mean = mean(b)
    a_centered = [x - a_mean for x in a]
    b_centered = [x - b_mean for x in b]
    denominator = sqrt(sum(x * x for x in a_centered) * sum(y * y for y in b_centered))
    if denominator == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a_centered, b_centered)) / denominator


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    denominator = sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    if denominator == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / denominator


def _sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _classification(agreement: float, external_effect: float) -> str:
    if external_effect == 0.0:
        return "null"
    if agreement == 1.0:
        return "consistent"
    if agreement == 0.0:
        return "discordant"
    return "context_dependent"


def validate_external_effect(
    external_effect: Mapping[str, float],
    reference_effects: Mapping[str, Mapping[str, float]],
    *,
    reference_dataset_id: str,
    external_dataset_id: str,
) -> ExternalValidationResult:
    """Compare an external cohort's effect against frozen reference transitions.

    ``reference_effects`` must be frozen effects from development data. No
    centering, scaling, feature selection, or fitting is performed here.
    """
    if not external_effect or not reference_effects:
        raise ValueError("external_effect and reference_effects cannot be empty")
    domains = _shared_domains(external_effect, *reference_effects.values())

    external_values = [float(external_effect[d]) for d in domains]
    direction_transfer: dict[str, DirectionTransfer] = {}
    similarities: dict[str, ReferenceSimilarity] = {}
    for domain in domains:
        ext = float(external_effect[domain])
        refs = {name: float(effect[domain]) for name, effect in reference_effects.items()}
        nonzero_refs = [value for value in refs.values() if value != 0.0]
        agreement = 0.0 if not nonzero_refs else sum(
            _sign(ext) == _sign(value) for value in nonzero_refs
        ) / len(nonzero_refs)
        direction_transfer[domain] = DirectionTransfer(
            external_effect=ext,
            reference_effects=refs,
            sign_agreement_fraction=round(agreement, 12),
            classification=_classification(agreement, ext),
        )

    for name, effect in reference_effects.items():
        ref_values = [float(effect[d]) for d in domains]
        similarities[name] = ReferenceSimilarity(
            pearson_r=round(_pearson(external_values, ref_values), 12),
            cosine_similarity=round(_cosine(external_values, ref_values), 12),
        )

    return ExternalValidationResult(
        reference_dataset_id=reference_dataset_id,
        external_dataset_id=external_dataset_id,
        domains=domains,
        external_effect={domain: round(float(external_effect[domain]), 12) for domain in domains},
        direction_transfer=direction_transfer,
        reference_similarity=similarities,
        overall_effect_l1=round(sum(abs(value) for value in external_values), 12),
        overall_effect_l2=round(sqrt(sum(value * value for value in external_values)), 12),
    )


def classify_transferability(result: ExternalValidationResult) -> dict[str, tuple[str, float]]:
    """Return a compact domain-level transferability summary."""
    return {
        domain: (item.classification, item.sign_agreement_fraction)
        for domain, item in result.direction_transfer.items()
    }
