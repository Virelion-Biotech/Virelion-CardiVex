from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .model_evaluation import classification_report
from .modeling import CentroidModel, Prediction, fit_centroid_model


@dataclass(frozen=True)
class ModelSpec:
    name: str
    version: str
    feature_names: tuple[str, ...]


@dataclass(frozen=True)
class FoldResult:
    fold: int
    accuracy: float
    balanced_accuracy: float
    macro_f1: float
    n_train: int
    n_test: int


@dataclass(frozen=True)
class CrossValidationResult:
    model: ModelSpec
    folds: tuple[FoldResult, ...]
    mean_accuracy: float
    mean_balanced_accuracy: float
    mean_macro_f1: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _fold_indices(labels: Sequence[str], k: int) -> tuple[tuple[int, ...], ...]:
    if len(labels) < 2:
        raise ValueError("at least two samples are required")
    if not 2 <= k <= len(labels):
        raise ValueError("k must be between 2 and the number of samples")
    groups: list[list[int]] = [[] for _ in range(k)]
    by_label: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        by_label.setdefault(str(label), []).append(index)
    for indices in by_label.values():
        for offset, index in enumerate(indices):
            groups[offset % k].append(index)
    return tuple(tuple(sorted(group)) for group in groups)


def cross_validate_centroid(
    states: Sequence[Mapping[str, float]],
    labels: Sequence[str],
    *,
    k: int = 5,
    feature_names: Sequence[str] | None = None,
    model_name: str = "centroid",
    model_version: str = "1.0.0",
) -> CrossValidationResult:
    """Run deterministic, class-aware k-fold validation for the transparent baseline."""
    if len(states) != len(labels):
        raise ValueError("states and labels must have equal length")
    names = tuple(feature_names or sorted({key for row in states for key in row}))
    if not names:
        raise ValueError("at least one feature is required")
    folds = _fold_indices(labels, k)
    results: list[FoldResult] = []
    all_indices = set(range(len(states)))
    for fold_number, test_indices in enumerate(folds, 1):
        test_set = set(test_indices)
        train_indices = tuple(sorted(all_indices - test_set))
        train_labels = [labels[i] for i in train_indices]
        if len(set(train_labels)) < len(set(labels)):
            raise ValueError("a fold's training set is missing at least one class")
        model: CentroidModel = fit_centroid_model(
            [states[i] for i in train_indices],
            train_labels,
            feature_names=names,
        )
        predictions = model.predict([states[i] for i in test_indices])
        observed = [labels[i] for i in test_indices]
        report = classification_report([p.label for p in predictions], observed)
        results.append(FoldResult(
            fold_number,
            report.accuracy,
            report.balanced_accuracy,
            report.macro_f1,
            len(train_indices),
            len(test_indices),
        ))
    return CrossValidationResult(
        model=ModelSpec(model_name, model_version, names),
        folds=tuple(results),
        mean_accuracy=sum(r.accuracy for r in results) / len(results),
        mean_balanced_accuracy=sum(r.balanced_accuracy for r in results) / len(results),
        mean_macro_f1=sum(r.macro_f1 for r in results) / len(results),
    )


def predict_with_model(
    model: CentroidModel,
    states: Sequence[Mapping[str, float]],
) -> tuple[Prediction, ...]:
    return tuple(model.predict(states))
