from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

from .audit import build_audit_record
from .benchmark_factory import BenchmarkManifest, audit_manifest, build_manifest
from .benchmark_report import summarize_manifest
from .features import CardiacState
from .pipeline import ChallengeAssessment, assess_scenario
from .splits import BenchmarkSplit, make_split
from .validation import validate_scenario


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    status: str
    assessment: ChallengeAssessment | None
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        return payload


@dataclass(frozen=True)
class BenchmarkRun:
    name: str
    manifest: BenchmarkManifest
    split: BenchmarkSplit
    results: tuple[ScenarioResult, ...]
    audit: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "manifest": {
                "name": self.manifest.name,
                "version": self.manifest.version,
                "ids": self.manifest.ids(),
            },
            "split": {
                "train": tuple(s.scenario_id for s in self.split.train),
                "validation": tuple(s.scenario_id for s in self.split.validation),
                "test": tuple(s.scenario_id for s in self.split.test),
                "held_out_novel": tuple(s.scenario_id for s in self.split.held_out_novel),
            },
            "results": [item.to_dict() for item in self.results],
            "audit": dict(self.audit),
        }


def run_benchmark_suite(
    scenarios: Iterable,
    *,
    baseline: CardiacState,
    known_states: Sequence[CardiacState] = (),
    name: str = "cardivex-benchmark",
    version: str = "0.1.0",
    abnormal_threshold: float = 0.20,
    novelty_threshold: float = 0.35,
) -> BenchmarkRun:
    """Execute the transparent benchmark baseline over a validated scenario suite.

    This runner evaluates downstream phenotype states only. It does not construct
    initiating biological agents or operational challenge procedures.
    """
    items = tuple(scenarios)
    manifest = build_manifest(items, name=name, version=version)
    split = make_split(items)
    issues = [issue for scenario in items for issue in validate_scenario(scenario)]
    if issues:
        raise ValueError("invalid scenarios remain after manifest validation")

    train = split.train + split.validation + split.test
    audit = audit_manifest(train, split.held_out_novel, novelty_threshold=novelty_threshold)
    if not audit["clean"]:
        raise ValueError("benchmark suite failed leakage or novelty audit")

    results: list[ScenarioResult] = []
    for scenario in items:
        try:
            assessment = assess_scenario(
                scenario,
                baseline=baseline,
                known_states=known_states,
                abnormal_threshold=abnormal_threshold,
                novelty_threshold=novelty_threshold,
            )
            results.append(ScenarioResult(scenario.scenario_id, "ok", assessment))
        except Exception as exc:  # preserve per-scenario diagnostics
            results.append(ScenarioResult(scenario.scenario_id, "error", None, (str(exc),)))

    return BenchmarkRun(name=name, manifest=manifest, split=split, results=tuple(results), audit=audit)


def build_run_audit(
    run: BenchmarkRun,
    *,
    run_id: str,
    model_version: str = "deterministic-baseline-v1",
    feature_pipeline_version: str = "cardivex-v1",
    seed: int | None = None,
    config: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Create a reproducible audit record for an executed benchmark run."""
    payload = run.to_dict()
    return build_audit_record(
        run_id=run_id,
        scenario_id=f"SUITE:{run.name}",
        scenario_version=run.manifest.version,
        model_version=model_version,
        feature_pipeline_version=feature_pipeline_version,
        config=dict(config or {}),
        seed=seed,
        input_payload=payload,
    )


def report_summary(run: BenchmarkRun) -> dict[str, object]:
    """Return a compact benchmark summary suitable for JSON/YAML export."""
    summary = summarize_manifest(
        run.manifest,
        train=run.split.train + run.split.validation + run.split.test,
        held_out=run.split.held_out_novel,
    )
    return summary.to_dict()
