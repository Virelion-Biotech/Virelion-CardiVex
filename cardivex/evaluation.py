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
    """Choose the threshold maximizing balanced accuracy, then sensitivity.

    Lower thresholds win a complete metric tie because the primary defensive
    objective is to avoid missing abnormal states.
    """
    if not results:
        raise ValueError("results cannot be empty")
    return max(results, key=lambda r: (r.balanced_accuracy, r.sensitivity, -r.threshold))


def ood_evaluate(
    known_states: Sequence[Mapping[str, float]],
    novel_states: Sequence[Mapping[str, float]],
    *,
    threshold: float,
    reference_states: Sequence[Mapping[str, float]] | None = None,
) -> OODResult:
    """Evaluate nearest-reference OOD detection without self-distance leakage.

    When ``reference_states`` is omitted, known states are scored leave-one-out.
    For a production benchmark, a separate development/reference set should be
    supplied explicitly and kept isolated from the scored known-test set.
    """
    if not known_states or not novel_states:
        raise ValueError("known_states and novel_states must both be non-empty")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")

    references = list(reference_states) if reference_states is not None else None
    if references is not None and not references:
        raise ValueError("reference_states cannot be empty when provided")

    known_scores: list[float] = []
    for index, state in enumerate(known_states):
        refs = references if references is not None else list(known_states[:index]) + list(known_states[index + 1:])
        if not refs:
            raise ValueError("at least two known states are required for leave-one-out OOD evaluation")
        known_scores.append(nearest_state_distance(state, refs))

    novel_scores = [nearest_state_distance(state, references or list(known_states)) for state in novel_states]
    tpr = sum(score >= threshold for score in novel_scores) / len(novel_scores)
    fpr = sum(score >= threshold for score in known_scores) / len(known_scores)
    return OODResult(threshold, tpr, fpr, len(known_states), len(novel_states))


def state_abnormality_scores(
    baseline: CardiacState,
    states: Iterable[CardiacState],
) -> list[float]:
    baseline_features = baseline.merged_features()
    return [abnormality_score(baseline_features, state.merged_features()) for state in states]
