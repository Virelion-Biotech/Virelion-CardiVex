from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ClassificationReport:
    accuracy: float
    balanced_accuracy: float
    macro_f1: float
    labels: tuple[str, ...]


def classification_report(predicted: Sequence[str], observed: Sequence[str]) -> ClassificationReport:
    if len(predicted) != len(observed) or not observed:
        raise ValueError("predicted and observed must have equal non-zero length")
    labels = tuple(sorted(set(predicted) | set(observed)))
    accuracy = sum(p == y for p, y in zip(predicted, observed)) / len(observed)

    recalls: list[float] = []
    f1s: list[float] = []
    for label in labels:
        tp = sum(p == label and y == label for p, y in zip(predicted, observed))
        fn = sum(p != label and y == label for p, y in zip(predicted, observed))
        fp = sum(p == label and y != label for p, y in zip(predicted, observed))
        recall = tp / (tp + fn) if tp + fn else 0.0
        precision = tp / (tp + fp) if tp + fp else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        recalls.append(recall)
        f1s.append(f1)
    return ClassificationReport(
        accuracy=accuracy,
        balanced_accuracy=sum(recalls) / len(recalls),
        macro_f1=sum(f1s) / len(f1s),
        labels=labels,
    )
