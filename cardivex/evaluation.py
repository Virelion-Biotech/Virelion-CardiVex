from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence

from .defense import abnormality_score, nearest_state_distance
from .features import CardiacState


@dataclass(frozen=True)
class CalibrationResult:
    threshold: float
    balanced_accuracy: float
    sensitivity: float
    specificity: float


@dataclass(frozen=True)
class OODResult:
    threshold: float
    true_positive_rate: float
    false_positive_rate: float
    known_count: int
    novel_count: int


def _validate_scores(scores: Sequence[float]) -> None:
    if not scores:
        raise ValueError("scores cannot be empty")
    if any(not isfinite(float(x)) for x in scores):
        raise ValueError("scores must be finite")


def calibration_curve(
    scores: Sequence[float],
    labels: Sequence[bool],
    *,
    thresholds: Iterable[float] | None = None,
) -> list[CalibrationResult]:
    """Evaluate binary abnormality thresholds on labeled benchmark scores."""
    if len(scores) != len(labels) or not scores:
        raise ValueError("scores and labels must have equal non-zero length")
    _validate_scores(scores)
    grid = list(thresholds) if thresholds is not None else [i / 20 for i in range(21)]
    results: list[CalibrationResult] = []
    positives = sum(bool(x) for x in labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("calibration requires both positive and negative labels")
    for threshold in grid:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("thresholds must be in [0, 1]")
        predicted = [score >= threshold for score in scores]
        tp = sum(p and y for p, y in zip(predicted, labels))
        tn = sum((not p) and (not y) for p, y in zip(predicted, labels))
        sensitivity = tp / positives
        specificity = tn / negatives
        results.append(
            CalibrationResult(
                threshold=threshold,
                balanced_accuracy=(sensitivity + specificity) / 2,
                sensitivity=sensitivity,
                specificity=specificity,
            )
        )
    return results


def best_threshold(results: Sequence[CalibrationResult]) -> CalibrationResult:
    if not results:
        raise ValueError("results cannot be empty")
    return max(results, key=lambda r: (r.balanced_accuracy, r.sensitivity, -r.threshold))


def ood_evaluate(
    known_states: Sequence[Mapping[str, float]],
    novel_states: Sequence[Mapping[str, float]],
    *,
    threshold: float,
) -> OODResult:
    """Evaluate a nearest-known-state OOD baseline at a fixed threshold."""
    if not known_states or not novel_states:
        raise ValueError("known_states and novel_states must both be non-empty")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    known_scores = [nearest_state_distance(state, list(known_states)) for state in known_states]
    novel_scores = [nearest_state_distance(state, list(known_states)) for state in novel_states]
    tpr = sum(score >= threshold for score in novel_scores) / len(novel_scores)
    fpr = sum(score >= threshold for score in known_scores) / len(known_scores)
    return OODResult(threshold, tpr, fpr, len(known_states), len(novel_states))


def state_abnormality_scores(
    baseline: CardiacState,
    states: Iterable[CardiacState],
) -> list[float]:
    baseline_features = baseline.merged_features()
    return [abnormality_score(baseline_features, state.merged_features()) for state in states]
