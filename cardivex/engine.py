from __future__ import annotations

import random
from dataclasses import replace
from typing import Iterable

from .models import DomainValue, Scenario, ScenarioState


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def generate_variations(
    scenario: Scenario,
    *,
    count: int = 8,
    seed: int | None = 0,
    max_deviation: float | None = None,
) -> list[Scenario]:
    """Generate bounded phenotype-level challenge variants.

    Variants modify only measurable host-response features. They retain a
    provenance link to the parent scenario and never encode initiating-agent
    procedures or operational parameters.
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    rng = random.Random(seed)
    configured = scenario.variation_space.get("max_deviation", 0.1)
    deviation = configured if max_deviation is None else max_deviation
    if not 0.0 <= deviation <= 1.0:
        raise ValueError("max_deviation must be in [0, 1]")
    allowed = set(scenario.variation_space.get("allowed_domains", scenario.phenotype_domains))

    variants: list[Scenario] = []
    for index in range(count):
        domains = dict(scenario.phenotype_domains)
        for name, original in scenario.phenotype_domains.items():
            if name not in allowed:
                continue
            delta = rng.uniform(-deviation, deviation)
            domains[name] = replace(
                original,
                value=_clip(original.value + delta),
                uncertainty=_clip(original.uncertainty + abs(delta) * 0.25),
                evidence_status="modeled",
            )
        variants.append(
            replace(
                scenario,
                scenario_id=f"{scenario.scenario_id}-V{index + 1:03d}",
                version="0.1.0",
                name=f"{scenario.name} variation {index + 1}",
                phenotype_domains=domains,
                ood_status="validation" if scenario.ood_status == "train" else scenario.ood_status,
                provenance_transformations=scenario.provenance_transformations
                + (f"bounded_variation(seed={seed},deviation={deviation})",),
            )
        )
    return variants


def interpolate_timeline(
    states: Iterable[ScenarioState],
    *,
    step: float = 1.0,
) -> list[ScenarioState]:
    """Linearly interpolate an ordered phenotype timeline.

    This works only on abstract measured domains and is intended for temporal
    benchmarking and digital-surrogate generation.
    """
    states = sorted(states, key=lambda s: s.relative_time)
    if len(states) < 2:
        raise ValueError("at least two states are required")
    if step <= 0:
        raise ValueError("step must be positive")

    result: list[ScenarioState] = []
    for left, right in zip(states, states[1:]):
        if right.relative_time <= left.relative_time:
            raise ValueError("relative_time values must be strictly increasing")
        t = left.relative_time
        while t < right.relative_time - 1e-9:
            alpha = (t - left.relative_time) / (right.relative_time - left.relative_time)
            names = set(left.domains) | set(right.domains)
            domains: dict[str, DomainValue] = {}
            for name in names:
                lv = left.domains.get(name, DomainValue(0.0)).value
                rv = right.domains.get(name, DomainValue(0.0)).value
                value = lv + alpha * (rv - lv)
                domains[name] = DomainValue(value=value, evidence_status="modeled")
            result.append(ScenarioState(state=left.state, relative_time=t, domains=domains))
            t += step
    result.append(states[-1])
    return result
