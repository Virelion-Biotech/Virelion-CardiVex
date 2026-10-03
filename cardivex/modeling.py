from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Mapping, Sequence

from .defense import abnormality_score


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float
    distance: float


@dataclass(frozen=True)
class CentroidModel:
    """Transparent nearest-centroid baseline over normalized feature maps."""

    centroids: Mapping[str, Mapping[str, float]]
    feature_names: tuple[str, ...]

    def predict_one(self, state: Mapping[str, float]) -> Prediction:
        if not self.centroids:
            raise ValueError("model has no centroids")
        distances = {
            label: abnormality_score(centroid, state)
            for label, centroid in self.centroids.items()
        }
        label, distance = min(distances.items(), key=lambda item: (item[1], item[0]))
        confidence = max(0.0, min(1.0, 1.0 - distance))
        return Prediction(label=label, confidence=confidence, distance=distance)

    def predict(self, states: Sequence[Mapping[str, float]]) -> list[Prediction]:
        return [self.predict_one(state) for state in states]


def _centroid(rows: Sequence[Mapping[str, float]], feature_names: tuple[str, ...]) -> dict[str, float]:
    if not rows:
        raise ValueError("cannot compute centroid from empty rows")
    return {
        name: sum(float(row.get(name, 0.0)) for row in rows) / len(rows)
        for name in feature_names
    }


def fit_centroid_model(
    states: Sequence[Mapping[str, float]],
    labels: Sequence[str],
    *,
    feature_names: Sequence[str] | None = None,
) -> CentroidModel:
    """Fit a dependency-free baseline model.

    This model is intended as a transparent benchmark, not as the final ML
    architecture. All inputs are already processed feature representations.
    """
    if not states or len(states) != len(labels):
        raise ValueError("states and labels must have equal non-zero length")
    names = tuple(feature_names or sorted({key for row in states for key in row}))
    if not names:
        raise ValueError("at least one feature is required")
    groups: dict[str, list[Mapping[str, float]]] = {}
    for state, label in zip(states, labels):
        groups.setdefault(str(label), []).append(state)
    return CentroidModel(
        centroids={label: _centroid(rows, names) for label, rows in sorted(groups.items())},
        feature_names=names,
    )


def accuracy(predicted: Sequence[str], observed: Sequence[str]) -> float:
    if len(predicted) != len(observed) or not observed:
        raise ValueError("predicted and observed must have equal non-zero length")
    return sum(p == y for p, y in zip(predicted, observed)) / len(observed)
