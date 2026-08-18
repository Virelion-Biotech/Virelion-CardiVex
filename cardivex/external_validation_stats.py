from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from statistics import mean
from typing import Sequence


@dataclass(frozen=True)
class ExactPermutationResult:
    observed_difference: float
    p_value_two_sided: float
    permutation_count: int
    cliff_delta: float


def exact_two_group_permutation(a: Sequence[float], b: Sequence[float]) -> ExactPermutationResult:
    """Exact two-sided permutation test for the difference in means.

    This is intentionally small-n friendly and does not assume asymptotic
    normality. It performs exhaustive relabeling, so for 3-vs-3 groups the
    smallest attainable two-sided p-value is 0.1.
    """
    if len(a) < 1 or len(b) < 1:
        raise ValueError("both groups must be non-empty")
    values = tuple(float(x) for x in a) + tuple(float(x) for x in b)
    n_a = len(a)
    observed = mean(b) - mean(a)
    permutation_differences: list[float] = []
    for chosen in combinations(range(len(values)), n_a):
        chosen_set = set(chosen)
        left = [values[i] for i in chosen]
        right = [values[i] for i in range(len(values)) if i not in chosen_set]
        permutation_differences.append(mean(right) - mean(left))
    extreme = sum(abs(diff) >= abs(observed) - 1e-15 for diff in permutation_differences)
    total = len(permutation_differences)
    wins = sum(x > y for x in b for y in a)
    losses = sum(x < y for x in b for y in a)
    cliff_delta = (wins - losses) / (len(a) * len(b))
    return ExactPermutationResult(
        observed_difference=observed,
        p_value_two_sided=extreme / total,
        permutation_count=total,
        cliff_delta=cliff_delta,
    )


def rmse_to_reference(
    vector: dict[str, float],
    reference: dict[str, float],
) -> float:
    """Unweighted RMSE across shared phenotype domains."""
    domains = sorted(set(vector) & set(reference))
    if not domains:
        raise ValueError("vectors have no shared domains")
    return (
        sum((float(vector[d]) - float(reference[d])) ** 2 for d in domains) / len(domains)
    ) ** 0.5
