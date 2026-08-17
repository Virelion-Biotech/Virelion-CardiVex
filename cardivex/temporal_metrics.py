from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence


@dataclass(frozen=True)
class TrajectoryError:
    mae: float
    max_error: float
    point_count: int
    domain_count: int

    @property
    def similarity(self) -> float:
        return max(0.0, min(1.0, 1.0 - self.mae))


def trajectory_error(
    predicted: Mapping[str, Sequence[tuple[float, float]]],
    observed: Mapping[str, Sequence[tuple[float, float]]],
) -> TrajectoryError:
    """Compare trajectories at shared timestamps without interpolation."""
    errors: list[float] = []
    domain_count = 0
    for domain in sorted(set(predicted) & set(observed)):
        p = {float(t): float(v) for t, v in predicted[domain]}
        o = {float(t): float(v) for t, v in observed[domain]}
        shared = sorted(set(p) & set(o))
        if not shared:
            continue
        domain_count += 1
        for time in shared:
            if not (isfinite(p[time]) and isfinite(o[time])):
                raise ValueError("trajectory values must be finite")
            errors.append(abs(p[time] - o[time]))
    if not errors:
        raise ValueError("predicted and observed trajectories have no shared points")
    mae = sum(errors) / len(errors)
    return TrajectoryError(
        mae=mae,
        max_error=max(errors),
        point_count=len(errors),
        domain_count=domain_count,
    )


def temporal_shift_error(
    reference: Mapping[str, Sequence[tuple[float, float]]],
    shifted: Mapping[str, Sequence[tuple[float, float]]],
) -> TrajectoryError:
    """Score a temporally shifted trajectory against its reference."""
    return trajectory_error(shifted, reference)
