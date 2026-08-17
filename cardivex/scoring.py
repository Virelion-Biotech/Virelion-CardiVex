from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .benchmark import evaluate_recovery
from .defense import abnormality_score, nearest_state_distance
from .features import CardiacState
from .pipeline import ChallengeAssessment


@dataclass(frozen=True)
class ModalityDetectionScore:
    modality: str
    abnormality: float
    novelty: float
    available: bool


@dataclass(frozen=True)
class AssessmentScore:
    overall_abnormality: float
    overall_novelty: float
    modality_scores: tuple[ModalityDetectionScore, ...]
    attribution_coverage: float


def _modality_domains(state: CardiacState, modality: str) -> Mapping[str, float]:
    vector = getattr(state, modality)
    return {} if vector is None else vector.values


def score_modalities(
    baseline: CardiacState,
    challenged: CardiacState,
    known_states: Iterable[CardiacState] = (),
) -> tuple[ModalityDetectionScore, ...]:
    references = tuple(known_states)
    scores: list[ModalityDetectionScore] = []
    for modality in ("imaging", "functional", "omics"):
        baseline_values = _modality_domains(baseline, modality)
        query_values = _modality_domains(challenged, modality)
        available = bool(baseline_values or query_values)
        if not available:
            scores.append(ModalityDetectionScore(modality, 0.0, 0.0, False))
            continue
        abnormality = abnormality_score(baseline_values, query_values)
        refs = [_modality_domains(state, modality) for state in references]
        refs = [reference for reference in refs if reference]
        novelty = nearest_state_distance(query_values, refs) if refs else 1.0
        scores.append(ModalityDetectionScore(modality, abnormality, novelty, True))
    return tuple(scores)


def score_assessment(
    assessment: ChallengeAssessment,
    *,
    baseline: CardiacState,
    known_states: Iterable[CardiacState] = (),
    attribution_threshold: float = 0.05,
) -> AssessmentScore:
    """Summarize an assessment without treating attribution as causal inference."""
    if not 0.0 <= attribution_threshold <= 1.0:
        raise ValueError("attribution_threshold must be in [0, 1]")
    challenged = assessment.challenged_state
    modality_scores = score_modalities(baseline, challenged, known_states)
    contributions = [item for item in assessment.attribution if item.contribution >= attribution_threshold]
    total_domains = len(assessment.attribution)
    attribution_coverage = len(contributions) / total_domains if total_domains else 0.0
    return AssessmentScore(
        overall_abnormality=assessment.detection.abnormality,
        overall_novelty=assessment.detection.novelty,
        modality_scores=modality_scores,
        attribution_coverage=attribution_coverage,
    )


def score_recovery(
    baseline: CardiacState,
    challenged: CardiacState,
    treated: CardiacState,
) -> dict[str, float]:
    result = evaluate_recovery(baseline, challenged, treated)
    return {
        "structural": result.structural,
        "functional": result.functional,
        "molecular": result.molecular,
        "overall": result.overall,
    }
