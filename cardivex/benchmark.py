from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .defense import abnormality_score, nearest_state_distance, rescue_score
from .features import CardiacState


@dataclass(frozen=True)
class DetectionResult:
    abnormality: float
    novelty: float
    is_abnormal: bool
    is_novel: bool


@dataclass(frozen=True)
class RecoveryResult:
    structural: float
    functional: float
    molecular: float
    overall: float


def detect_state(
    baseline: Mapping[str, float],
    query: Mapping[str, float],
    known_states: Iterable[Mapping[str, float]],
    *,
    abnormal_threshold: float = 0.20,
    novelty_threshold: float = 0.35,
) -> DetectionResult:
    """Run deterministic baseline-abnormality and nearest-state novelty tests."""
    if not 0.0 <= abnormal_threshold <= 1.0:
        raise ValueError("abnormal_threshold must be in [0, 1]")
    if not 0.0 <= novelty_threshold <= 1.0:
        raise ValueError("novelty_threshold must be in [0, 1]")
    references = list(known_states)
    abnormality = abnormality_score(baseline, query)
    novelty = nearest_state_distance(query, references) if references else 1.0
    return DetectionResult(
        abnormality=abnormality,
        novelty=novelty,
        is_abnormal=abnormality >= abnormal_threshold,
        is_novel=novelty >= novelty_threshold,
    )


def evaluate_recovery(
    baseline: CardiacState,
    challenged: CardiacState,
    treated: CardiacState,
) -> RecoveryResult:
    """Compare modality-level recovery toward a common baseline."""
    def modality_score(name: str) -> float:
        b = baseline.merged_features()
        c = challenged.merged_features()
        t = treated.merged_features()
        keys = {k for k in b | c | t if k.startswith(f"{name}:")}
        if not keys:
            return 0.0
        return rescue_score(
            {k: b.get(k, 0.0) for k in keys},
            {k: c.get(k, 0.0) for k in keys},
            {k: t.get(k, 0.0) for k in keys},
        )

    structural = max(
        0.0,
        modality_score("imaging"),
    )
    functional = max(
        0.0,
        modality_score("functional"),
    )
    molecular = max(
        0.0,
        modality_score("omics"),
    )
    available = [x for x in (structural, functional, molecular) if x > 0.0 or any(
        key.startswith(prefix + ":") for key in baseline.merged_features()
        for prefix in ("imaging", "functional", "omics")
    )]
    overall = sum(available) / len(available) if available else rescue_score(
        baseline.domain_scores, challenged.domain_scores, treated.domain_scores
    )
    return RecoveryResult(structural, functional, molecular, max(-1.0, min(1.0, overall)))
