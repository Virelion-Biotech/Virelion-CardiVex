from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .challenge_families import ChallengeFamily, FAMILIES, family_is_novel
from .models import Scenario
from .validation import detect_direct_leakage, validate_scenario


@dataclass(frozen=True)
class BenchmarkManifest:
    name: str
    version: str
    scenarios: tuple[Scenario, ...]
    family_names: tuple[str, ...]

    def ids(self) -> tuple[str, ...]:
        return tuple(s.scenario_id for s in self.scenarios)


def build_manifest(
    scenarios: Iterable[Scenario],
    *,
    name: str = "cardivex-challenge-suite",
    version: str = "0.1.0",
) -> BenchmarkManifest:
    items = tuple(sorted(scenarios, key=lambda s: s.scenario_id))
    if not items:
        raise ValueError("at least one scenario is required")
    ids = [s.scenario_id for s in items]
    if len(set(ids)) != len(ids):
        raise ValueError("scenario IDs must be unique")
    issues = [issue for scenario in items for issue in validate_scenario(scenario)]
    if issues:
        raise ValueError("manifest contains invalid scenarios: " + ", ".join(i.code for i in issues))
    family_names = tuple(sorted({
        "held_out_novel" if s.ood_status == "held_out_novel" else "familiar"
        for s in items
    }))
    return BenchmarkManifest(name=name, version=version, scenarios=items, family_names=family_names)


def audit_manifest(
    train: Sequence[Scenario],
    held_out: Sequence[Scenario],
    *,
    novelty_threshold: float = 0.35,
) -> dict[str, object]:
    leakage = detect_direct_leakage(train, held_out)
    novelty = {
        scenario.scenario_id: family_is_novel(scenario, train, threshold=novelty_threshold)
        for scenario in held_out
    }
    return {
        "train_count": len(train),
        "held_out_count": len(held_out),
        "leakage_issues": [issue.code for issue in leakage],
        "novelty": novelty,
        "clean": not leakage and all(novelty.values()),
    }


def available_families() -> tuple[ChallengeFamily, ...]:
    return FAMILIES
