from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Mapping, Sequence

from .modeling import CentroidModel, Prediction, fit_centroid_model, accuracy


@dataclass(frozen=True)
class ModelSpec:
    name: str
    version: str
    feature_names: tuple[str, ...]


@dataclass(frozen=True)
class FoldResult:
    fold: int
    accuracy: float
    n_train: int
    n_test: int


@dataclass(frozen=True)
class CrossValidationResult:
    model: ModelSpec
    folds: tuple[FoldResult, ...]
    mean_accuracy: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _fold_indices(n: int, k: int) -> tuple[tuple[int, ...], ...]:
    if n < 2:
        raise ValueError("at least two samples are required")
    if not 2 <= k <= n:
        raise ValueError("k must be between 2 and the number of samples")
    groups: list[list[int]] = [[] for _ in range(k)]
    for index in range(n):
        groups[index % k].append(index)
    return tuple(tuple(group) for group in groups)


def cross_validate_centroid(
    states: Sequence[Mapping[str, float]],
    labels: Sequence[str],
    *,
    k: int = 5,
    feature_names: Sequence[str] | None = None,
    model_name: str = "centroid",
    model_version: str = "1.0.0",
) -> CrossValidationResult:
    """Run deterministic k-fold validation for the transparent baseline."""
    if len(states) != len(labels):
        raise ValueError("states and labels must have equal length")
    names = tuple(feature_names or sorted({key for row in states for key in row}))
    if not names:
        raise ValueError("at least one feature is required")
    folds = _fold_indices(len(states), k)
    results: list[FoldResult] = []
    all_indices = set(range(len(states)))
    for fold_number, test_indices in enumerate(folds, 1):
        test_set = set(test_indices)
        train_indices = tuple(sorted(all_indices - test_set))
        model: CentroidModel = fit_centroid_model(
            [states[i] for i in train_indices],
            [labels[i] for i in train_indices],
            feature_names=names,
        )
        predictions = model.predict([states[i] for i in test_indices])
        score = accuracy([p.label for p in predictions], [labels[i] for i in test_indices])
        results.append(FoldResult(fold_number, score, len(train_indices), len(test_indices)))
    return CrossValidationResult(
        model=ModelSpec(model_name, model_version, names),
        folds=tuple(results),
        mean_accuracy=sum(r.accuracy for r in results) / len(results),
    )


def predict_with_model(
    model: CentroidModel,
    states: Sequence[Mapping[str, float]],
) -> tuple[Prediction, ...]:
    return tuple(model.predict(states))
