from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .models import Scenario
from .validation import detect_direct_leakage


@dataclass(frozen=True)
class BenchmarkSplit:
    train: tuple[Scenario, ...]
    validation: tuple[Scenario, ...]
    test: tuple[Scenario, ...]
    held_out_novel: tuple[Scenario, ...]

    def validate(self) -> None:
        groups = [self.train, self.validation, self.test, self.held_out_novel]
        ids: set[str] = set()
        for group in groups:
            for scenario in group:
                if scenario.scenario_id in ids:
                    raise ValueError(f"scenario appears in multiple splits: {scenario.scenario_id}")
                ids.add(scenario.scenario_id)
        leakage = detect_direct_leakage(self.train + self.validation + self.test, self.held_out_novel)
        if leakage:
            raise ValueError("held-out split contains direct leakage")
        for scenario in self.held_out_novel:
            if scenario.ood_status != "held_out_novel":
                raise ValueError(f"held-out scenario has incorrect status: {scenario.scenario_id}")


def make_split(scenarios: Iterable[Scenario]) -> BenchmarkSplit:
    """Partition scenarios using their declared benchmark status."""
    groups = {"train": [], "validation": [], "test": [], "held_out_novel": []}
    for scenario in scenarios:
        if scenario.ood_status not in groups:
            raise ValueError(f"unsupported split status: {scenario.ood_status}")
        groups[scenario.ood_status].append(scenario)
    split = BenchmarkSplit(*(tuple(sorted(groups[name], key=lambda s: s.scenario_id)) for name in groups))
    split.validate()
    return split
