from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

from .benchmark_factory import BenchmarkManifest, audit_manifest
from .calibration import domain_uncertainty, scenario_calibration_error
from .models import Scenario


@dataclass(frozen=True)
class BenchmarkSummary:
    scenario_count: int
    held_out_count: int
    family_counts: Mapping[str, int]
    leakage_free: bool
    all_novel_held_out: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def summarize_manifest(
    manifest: BenchmarkManifest,
    *,
    train: Iterable[Scenario] = (),
    held_out: Iterable[Scenario] = (),
    novelty_threshold: float = 0.35,
) -> BenchmarkSummary:
    items = tuple(manifest.scenarios)
    train_items = tuple(train)
    held_items = tuple(held_out)
    audit = audit_manifest(train_items, held_items, novelty_threshold=novelty_threshold) if train_items or held_items else {
        "leakage_issues": [],
        "novelty": {},
    }
    counts: dict[str, int] = {}
    for scenario in items:
        family = "held_out_novel" if scenario.ood_status == "held_out_novel" else "development"
        counts[family] = counts.get(family, 0) + 1
    all_novel = all(audit.get("novelty", {}).values()) if held_items else True
    return BenchmarkSummary(
        scenario_count=len(items),
        held_out_count=len(held_items),
        family_counts=counts,
        leakage_free=not bool(audit.get("leakage_issues")),
        all_novel_held_out=all_novel,
    )


def compare_scenario_to_observation(
    scenario: Scenario,
    observed_domain_scores: Mapping[str, float],
) -> dict[str, float]:
    return scenario_calibration_error(scenario.domain_vector(), observed_domain_scores)


def summarize_observation_uncertainty(
    observations: Iterable[Mapping[str, float]],
) -> dict[str, dict[str, float | int]]:
    return {
        domain: {
            "mean": band.mean,
            "lower": band.lower,
            "upper": band.upper,
            "count": band.count,
        }
        for domain, band in domain_uncertainty(observations).items()
    }
