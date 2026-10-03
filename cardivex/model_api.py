from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True)
class ModelPrediction:
    """Model output normalized to the CardiVex evaluation contract."""

    label: str
    score: float
    metadata: Mapping[str, str] = ()


class CardiVexModel(Protocol):
    """Minimal adapter contract for arbitrary predictive models.

    Adapters consume already-processed feature vectors. They must not perform
    acquisition, experimental procedures, or raw biological-agent design.
    """

    model_id: str
    model_version: str

    def predict(self, feature_rows: Sequence[Mapping[str, float]]) -> Sequence[ModelPrediction]:
        ...


def validate_model_predictions(
    predictions: Sequence[ModelPrediction],
    *,
    expected_count: int,
) -> None:
    if len(predictions) != expected_count:
        raise ValueError(
            f"model returned {len(predictions)} predictions for {expected_count} inputs"
        )
    for prediction in predictions:
        if not prediction.label.strip():
            raise ValueError("prediction label cannot be empty")
        if not 0.0 <= float(prediction.score) <= 1.0:
            raise ValueError("prediction score must be in [0, 1]")
