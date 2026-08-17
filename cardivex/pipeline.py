from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

from .attribution import DomainAttribution, attribute_domains
from .benchmark import DetectionResult, detect_state, evaluate_recovery, RecoveryResult
from .features import CardiacState
from .translation import scenario_to_multimodal, TranslationProfile
from .models import Scenario


@dataclass(frozen=True)
class ChallengeAssessment:
    scenario_id: str
    detection: DetectionResult
    attribution: tuple[DomainAttribution, ...]
    challenged_state: CardiacState

    def to_dict(self) -> dict:
        payload = asdict(self)
        return payload


@dataclass(frozen=True)
class EndToEndResult:
    assessment: ChallengeAssessment
    recovery: RecoveryResult | None = None

    def to_dict(self) -> dict:
        return {
            "assessment": self.assessment.to_dict(),
            "recovery": asdict(self.recovery) if self.recovery is not None else None,
        }


def assess_scenario(
    scenario: Scenario,
    *,
    baseline: CardiacState,
    known_states: Iterable[CardiacState] = (),
    profile: TranslationProfile | None = None,
    abnormal_threshold: float = 0.20,
    novelty_threshold: float = 0.35,
) -> ChallengeAssessment:
    """Run the deterministic defensive baseline on a scenario-derived state."""
    challenged = scenario_to_multimodal(scenario, profile=profile)
    baseline_domains = baseline.domain_scores
    known_domain_states = [state.domain_scores for state in known_states]
    detection = detect_state(
        baseline_domains,
        challenged.domain_scores,
        known_domain_states,
        abnormal_threshold=abnormal_threshold,
        novelty_threshold=novelty_threshold,
    )
    attribution = tuple(attribute_domains(baseline_domains, challenged.domain_scores))
    return ChallengeAssessment(
        scenario_id=scenario.scenario_id,
        detection=detection,
        attribution=attribution,
        challenged_state=challenged,
    )


def run_end_to_end(
    scenario: Scenario,
    *,
    baseline: CardiacState,
    known_states: Iterable[CardiacState] = (),
    treated_state: CardiacState | None = None,
    profile: TranslationProfile | None = None,
) -> EndToEndResult:
    assessment = assess_scenario(
        scenario,
        baseline=baseline,
        known_states=known_states,
        profile=profile,
    )
    recovery = None
    if treated_state is not None:
        recovery = evaluate_recovery(baseline, assessment.challenged_state, treated_state)
    return EndToEndResult(assessment=assessment, recovery=recovery)
