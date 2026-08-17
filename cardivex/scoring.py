from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .benchmark import DetectionResult, evaluate_recovery
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
        b = _modality_domains(baseline, modality)
        q = _modality_domains(challenged, modality)
        available = bool(b or q)
        if not available:
            scores.append(ModalityDetectionScore(modality, 0.0, 0.0, False))
            continue
        from .defense import abnormality_score, nearest_state_distance
        abnormality = abnormality_score(b, q)
        refs = [_modality_domains(state, modality) for state in references]
        refs = [r for r in refs if r]
        novelty = nearest_state_distance(q, refs) if refs else 1.0
        scores.append(ModalityDetectionScore(modality, abnormality, novelty, True))
    return tuple(scores)


def score_assessment(
    assessment: ChallengeAssessment,
    *,
    baseline: CardiacState,
    known_states: Iterable[CardiacState] = (),
) -> AssessmentScore:
    challenged = assessment.challenged_state
    modality_scores = score_modalities(baseline, challenged, known_states)
    available = [item for item in modality_scores if item.available]
    attribution_coverage = sum(item.contribution for item in assessment.attribution)
    return AssessmentScore(
        overall_abnormality=assessment.detection.abnormality,
        overall_novelty=assessment.detection.novelty,
        modality_scores=modality_scores,
        attribution_coverage=max(0.0, min(1.0, attribution_coverage)),
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
