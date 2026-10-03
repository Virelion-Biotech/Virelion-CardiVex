from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from .models import DomainValue, ScenarioState


def bounded_trajectory(
    challenge: Mapping[str, float],
    *,
    onset: float = 0.0,
    peak: float = 1.0,
    recovery: float = 2.0,
    recovery_fraction: float = 0.5,
) -> tuple[ScenarioState, ...]:
    """Create a simple bounded abstract trajectory from a challenge state."""
    if not (0.0 < peak < recovery):
        raise ValueError("times must satisfy onset < peak < recovery")
    if not 0.0 <= recovery_fraction <= 1.0:
        raise ValueError("recovery_fraction must be in [0, 1]")
    challenge_values = {k: float(v) for k, v in challenge.items()}
    zero = {k: DomainValue(0.0, evidence_status="modeled") for k in challenge_values}
    peak_state = {k: DomainValue(max(0.0, min(1.0, v)), evidence_status="modeled") for k, v in challenge_values.items()}
    recovery_state = {
        k: DomainValue(max(0.0, min(1.0, v * recovery_fraction)), evidence_status="modeled")
        for k, v in challenge_values.items()
    }
    return (
        ScenarioState("onset", onset, zero),
        ScenarioState("peak", peak, peak_state),
        ScenarioState("recovery", recovery, recovery_state),
    )


def shift_timeline(
    states: tuple[ScenarioState, ...],
    *,
    scale: float = 1.0,
    offset: float = 0.0,
) -> tuple[ScenarioState, ...]:
    """Apply bounded time scaling/offset without changing phenotype values."""
    if scale <= 0:
        raise ValueError("scale must be positive")
    return tuple(
        replace(state, relative_time=max(0.0, state.relative_time * scale + offset))
        for state in states
    )
