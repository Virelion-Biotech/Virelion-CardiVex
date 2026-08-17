from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .audit import build_audit_record
from .evaluation import calibration_curve
from .experiments import CrossValidationResult, cross_validate_centroid
from .model_registry import ModelRecord
from .modeling import fit_centroid_model
from .serialization import dumps


@dataclass(frozen=True)
class ExperimentResult:
    experiment_id: str
    model_record: ModelRecord
    cross_validation: CrossValidationResult
    calibration_threshold: float
    calibration_balanced_accuracy: float
    held_out_metrics: Mapping[str, float]
    audit: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _binary_metrics(scores: Sequence[float], labels: Sequence[int], threshold: float) -> dict[str, float]:
    predicted = [float(score) >= threshold for score in scores]
    positives = sum(1 for label in labels if int(label) == 1)
    negatives = len(labels) - positives
    tp = sum(p and int(y) == 1 for p, y in zip(predicted, labels))
    fp = sum(p and int(y) == 0 for p, y in zip(predicted, labels))
    tpr = tp / positives if positives else 0.0
    fpr = fp / negatives if negatives else 0.0
    return {"tpr": tpr, "fpr": fpr, "threshold": threshold}


def run_centroid_experiment(
    *,
    experiment_id: str,
    states: Sequence[Mapping[str, float]],
    labels: Sequence[str],
    calibration_scores: Sequence[float],
    calibration_labels: Sequence[int],
    known_states: Sequence[Mapping[str, float]],
    held_out_scores: Sequence[float],
    held_out_labels: Sequence[int],
    feature_names: Sequence[str] | None = None,
    k: int = 5,
    model_name: str = "centroid",
    model_version: str = "1.0.0",
    seed: int | None = 0,
) -> ExperimentResult:
    """Run the transparent baseline with frozen calibration and held-out scoring."""
    if not experiment_id.strip():
        raise ValueError("experiment_id cannot be empty")
    if len(calibration_scores) != len(calibration_labels) or not calibration_scores:
        raise ValueError("calibration scores and labels must have equal non-zero length")
    if len(held_out_scores) != len(held_out_labels) or not held_out_scores:
        raise ValueError("held-out scores and labels must have equal non-zero length")
    if not known_states:
        raise ValueError("known_states cannot be empty")

    cv = cross_validate_centroid(
        states, labels, k=k, feature_names=feature_names,
        model_name=model_name, model_version=model_version,
    )
    calibration = calibration_curve(calibration_scores, [bool(x) for x in calibration_labels])
    chosen = max(calibration, key=lambda r: (r.balanced_accuracy, r.sensitivity, -r.threshold))
    held_out = _binary_metrics(held_out_scores, held_out_labels, chosen.threshold)

    fit_centroid_model(states, labels, feature_names=feature_names)
    record = ModelRecord(
        model_id=f"MODEL-{experiment_id}",
        name=model_name,
        version=model_version,
        feature_contract="cardivex-v1",
        training_split="development",
        training_sample_count=len(states),
    )
    audit = build_audit_record(
        run_id=experiment_id,
        scenario_id="EXPERIMENT",
        scenario_version="1.0.0",
        model_version=model_version,
        feature_pipeline_version=record.feature_contract,
        config={"k": k, "threshold": chosen.threshold, "model_name": model_name},
        seed=seed,
        input_payload={
            "states": states,
            "labels": labels,
            "calibration_scores": calibration_scores,
            "calibration_labels": calibration_labels,
            "held_out_scores": held_out_scores,
            "held_out_labels": held_out_labels,
            "known_states": known_states,
        },
    )
    return ExperimentResult(
        experiment_id=experiment_id,
        model_record=record,
        cross_validation=cv,
        calibration_threshold=chosen.threshold,
        calibration_balanced_accuracy=chosen.balanced_accuracy,
        held_out_metrics=held_out,
        audit=audit,
    )


def experiment_json(result: ExperimentResult) -> str:
    return dumps(result)
