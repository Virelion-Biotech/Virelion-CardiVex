from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .audit import build_audit_record
from .evaluation import best_threshold, ood_evaluate
from .experiments import CrossValidationResult, cross_validate_centroid
from .model_registry import ModelRecord
from .modeling import CentroidModel, fit_centroid_model
from .serialization import dumps


@dataclass(frozen=True)
class ExperimentResult:
    experiment_id: str
    model_record: ModelRecord
    cross_validation: CrossValidationResult
    calibration_threshold: float
    held_out_ood: Mapping[str, float]
    audit: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


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
    """Run the transparent baseline with frozen calibration and held-out OOD evaluation."""
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
    threshold = best_threshold(calibration_scores, calibration_labels)
    ood = ood_evaluate(held_out_scores, held_out_labels, threshold=threshold)
    model: CentroidModel = fit_centroid_model(states, labels, feature_names=feature_names)
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
        config={"k": k, "threshold": threshold, "model_name": model_name},
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
        calibration_threshold=threshold,
        held_out_ood={"tpr": ood.tpr, "fpr": ood.fpr, "threshold": ood.threshold},
        audit=audit,
    )


def experiment_json(result: ExperimentResult) -> str:
    return dumps(result)
