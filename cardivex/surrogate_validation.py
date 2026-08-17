from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .features import CardiacState, ModalityVector
from .longitudinal import LongitudinalGroup, longitudinal_domain_series
from .models import Scenario
from .temporal_metrics import trajectory_error
from .translation import TranslationProfile, default_translation_profile


@dataclass(frozen=True)
class ModalityValidation:
    modality: str
    mae: float
    max_error: float
    evaluated_features: int
    evaluated_points: int


@dataclass(frozen=True)
class SurrogateValidation:
    """Validation summary for one scenario against a held-out observed trajectory."""

    scenario_id: str
    group_id: str
    domain_mae: float
    domain_max_error: float
    temporal_similarity: float
    evaluated_points: int
    evaluated_domains: int
    observed_dataset_ids: tuple[str, ...]
    modality_results: tuple[ModalityValidation, ...] = ()

    @property
    def acceptable(self) -> bool:
        return self.evaluated_points > 0 and self.evaluated_domains > 0

    @property
    def multimodal_mae(self) -> float:
        evaluated = [item.mae for item in self.modality_results if item.evaluated_features > 0]
        return sum(evaluated) / len(evaluated) if evaluated else 0.0


def _scenario_series(scenario: Scenario) -> dict[str, tuple[tuple[float, float], ...]]:
    domains = sorted(set().union(*(state.domains.keys() for state in scenario.temporal_profile)))
    return {
        domain: tuple(
            (float(state.relative_time), float(state.domains.get(domain, 0.0).value))
            for state in scenario.temporal_profile
        )
        for domain in domains
    }


def _project(domains: Mapping[str, float], rules: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    return {
        feature: max(0.0, min(1.0, sum(float(domains.get(domain, 0.0)) * float(weight) for domain, weight in weights.items())))
        for feature, weights in rules.items()
    }


def _state_to_multimodal(
    scenario: Scenario,
    state_index: int,
    profile: TranslationProfile,
) -> CardiacState:
    state = scenario.temporal_profile[state_index]
    domains = {name: float(value.value) for name, value in state.domains.items()}
    return CardiacState(
        imaging=ModalityVector("imaging", _project(domains, profile.imaging)),
        functional=ModalityVector("functional", _project(domains, profile.functional)),
        omics=ModalityVector("omics", _project(domains, profile.omics)),
        domain_scores=domains,
        time=float(state.relative_time),
        metadata={"scenario_id": scenario.scenario_id, "translation_profile": "surrogate-validation"},
    )


def _modality_error(
    predicted: Mapping[str, Mapping[float, Mapping[str, float]]],
    observed: Mapping[str, Mapping[float, Mapping[str, float]]],
    *,
    modality: str,
    time_tolerance: float,
) -> ModalityValidation:
    errors: list[float] = []
    points = 0
    predicted_points = predicted.get(modality, {})
    observed_points = observed.get(modality, {})
    for time, values in predicted_points.items():
        matches = [observed_time for observed_time in observed_points if abs(float(observed_time) - float(time)) <= time_tolerance]
        if not matches:
            continue
        observed_values = observed_points[min(matches, key=lambda item: abs(float(item) - float(time)))]
        shared = set(values) & set(observed_values)
        if not shared:
            continue
        points += 1
        errors.extend(abs(float(values[name]) - float(observed_values[name])) for name in shared)
    return ModalityValidation(
        modality=modality,
        mae=sum(errors) / len(errors) if errors else 0.0,
        max_error=max(errors, default=0.0),
        evaluated_features=len(errors),
        evaluated_points=points,
    )


def _aligned_observed(
    predicted: Mapping[str, tuple[tuple[float, float], ...]],
    observed: Mapping[str, tuple[tuple[float, float], ...]],
    *,
    tolerance: float,
) -> tuple[dict[str, tuple[tuple[float, float], ...]], dict[str, tuple[tuple[float, float], ...]]]:
    aligned_pred: dict[str, tuple[tuple[float, float], ...]] = {}
    aligned_obs: dict[str, tuple[tuple[float, float], ...]] = {}
    for domain in sorted(set(predicted) & set(observed)):
        observed_points = observed[domain]
        p_rows: list[tuple[float, float]] = []
        o_rows: list[tuple[float, float]] = []
        for time, value in predicted[domain]:
            matches = [point for point in observed_points if abs(float(point[0]) - float(time)) <= tolerance]
            if not matches:
                continue
            nearest = min(matches, key=lambda point: abs(float(point[0]) - float(time)))
            p_rows.append((float(time), float(value)))
            o_rows.append((float(time), float(nearest[1])))
        if p_rows:
            aligned_pred[domain] = tuple(p_rows)
            aligned_obs[domain] = tuple(o_rows)
    return aligned_pred, aligned_obs


def validate_scenario_against_group(
    scenario: Scenario,
    group: LongitudinalGroup,
    *,
    time_tolerance: float = 0.0,
    translation_profile: TranslationProfile | None = None,
) -> SurrogateValidation:
    """Compare a generated scenario trajectory with one held-out observed unit."""
    if time_tolerance < 0:
        raise ValueError("time_tolerance must be non-negative")
    predicted = _scenario_series(scenario)
    observed = longitudinal_domain_series(group)

    errors: list[float] = []
    domains = 0
    for domain in sorted(set(predicted) & set(observed)):
        matched = 0
        for time, value in predicted[domain]:
            candidates = [point for point in observed[domain] if abs(float(point[0]) - time) <= time_tolerance]
            if not candidates:
                continue
            observed_value = min(candidates, key=lambda point: abs(float(point[0]) - time))[1]
            errors.append(abs(float(value) - float(observed_value)))
            matched += 1
        if matched:
            domains += 1

    all_errors = tuple(errors)
    mae = sum(all_errors) / len(all_errors) if all_errors else 0.0
    max_error = max(all_errors, default=0.0)
    aligned_predicted, aligned_observed = _aligned_observed(predicted, observed, tolerance=time_tolerance)
    temporal = trajectory_error(aligned_predicted, aligned_observed) if all(aligned_predicted.values()) else None
    similarity = temporal.similarity if temporal is not None else 0.0

    profile = translation_profile or default_translation_profile()
    predicted_modalities: dict[str, dict[float, Mapping[str, float]]] = {"imaging": {}, "functional": {}, "omics": {}}
    for index, state in enumerate(scenario.temporal_profile):
        translated = _state_to_multimodal(scenario, index, profile)
        for modality in predicted_modalities:
            vector = getattr(translated, modality)
            if vector is not None:
                predicted_modalities[modality][float(state.relative_time)] = dict(vector.values)
    observed_modalities: dict[str, dict[float, Mapping[str, float]]] = {"imaging": {}, "functional": {}, "omics": {}}
    for record in group.records:
        for name in observed_modalities:
            vector = getattr(record.state, name)
            if vector is not None:
                observed_modalities[name][float(record.time)] = dict(vector.values)
    modality_results = tuple(
        _modality_error(predicted_modalities, observed_modalities, modality=name, time_tolerance=time_tolerance)
        for name in ("imaging", "functional", "omics")
    )

    return SurrogateValidation(
        scenario_id=scenario.scenario_id,
        group_id=group.group_id,
        domain_mae=mae,
        domain_max_error=max_error,
        temporal_similarity=similarity,
        evaluated_points=len(all_errors),
        evaluated_domains=domains,
        observed_dataset_ids=group.dataset_ids,
        modality_results=modality_results,
    )


def summarize_surrogate_validation(results: Iterable[SurrogateValidation]) -> dict[str, float | int]:
    """Summarize held-out surrogate validation without pooling experimental units blindly."""
    rows = tuple(results)
    if not rows:
        return {"groups": 0, "mean_domain_mae": 0.0, "mean_temporal_similarity": 0.0, "mean_multimodal_mae": 0.0}
    return {
        "groups": len(rows),
        "mean_domain_mae": sum(row.domain_mae for row in rows) / len(rows),
        "mean_temporal_similarity": sum(row.temporal_similarity for row in rows) / len(rows),
        "mean_multimodal_mae": sum(row.multimodal_mae for row in rows) / len(rows),
        "max_group_domain_mae": max(row.domain_mae for row in rows),
    }
