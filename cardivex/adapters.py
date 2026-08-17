from __future__ import annotations

from typing import Mapping

from .features import ModalityVector


def normalize_features(
    features: Mapping[str, float],
    *,
    lower: float = 0.0,
    upper: float = 1.0,
) -> dict[str, float]:
    """Clamp already processed measurements into the CardiVex feature range."""
    if lower >= upper:
        raise ValueError("lower must be less than upper")
    span = upper - lower
    normalized: dict[str, float] = {}
    for key, value in features.items():
        x = float(value)
        if x != x:
            raise ValueError(f"feature '{key}' is NaN")
        normalized[str(key)] = max(0.0, min(1.0, (x - lower) / span))
    return normalized


def imaging_features(features: Mapping[str, float]) -> ModalityVector:
    return ModalityVector("imaging", normalize_features(features))


def functional_features(features: Mapping[str, float]) -> ModalityVector:
    return ModalityVector("functional", normalize_features(features))


def omics_features(features: Mapping[str, float]) -> ModalityVector:
    return ModalityVector("omics", normalize_features(features))
