#!/usr/bin/env python3
"""Real-data validated benchmark + condition classification on GSE144424.

Uses development subjects only for reference states; held-out subjects
{19128, 18870, 18855} form held_out_novel scenarios and surrogate groups.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from cardivex.experiments import cross_validate_centroid
from cardivex.features import CardiacState, ModalityVector
from cardivex.geo_counts import (
    ModuleScoreConfig,
    parse_gse144424_count_metadata,
    read_geo_counts,
    score_count_modules,
)
from cardivex.longitudinal import LongitudinalGroup, collapse_subject_replicates
from cardivex.models import Confidence, DomainValue, EvidenceTier, Scenario, ScenarioState
from cardivex.suite import report_summary
from cardivex.validated_benchmark import run_validated_benchmark

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ROOT / "data" / "GSE144424_Counts_RNA_MCW_NEB.txt.gz"
MODULES = ROOT / "configs" / "gse144424_ensembl_modules.yaml"
REPORTS = ROOT / "reports"
EXPECTED_SHA = "cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c"
HELD_OUT = ("19128", "18870", "18855")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_ensembl_modules(path: Path) -> dict[str, tuple[str, ...]]:
    text = path.read_text(encoding="utf-8")
    modules: dict[str, tuple[str, ...]] = {}
    current: str | None = None
    for line in text.splitlines():
        mod = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if mod:
            current = mod.group(1)
            continue
        ens = re.match(r"^    ensembl:\s*\[(.*)\]\s*$", line)
        if ens and current is not None:
            values = [item.strip().strip("'\"") for item in ens.group(1).split(",") if item.strip()]
            modules[current] = tuple(values)
    if len(modules) < 3:
        raise ValueError(f"expected Ensembl modules in {path}")
    return modules


def dv(scores) -> dict[str, DomainValue]:
    return {k: DomainValue(float(v), evidence_status="observed") for k, v in scores.items()}


def state_from_record(record, *, split: str) -> CardiacState:
    return CardiacState(
        domain_scores=dict(record.state.domain_scores),
        omics=ModalityVector("omics", {"rna_module_features": 1.0}),
        time=float(record.time),
        metadata={
            "benchmark_split": split,
            "subject_id": str(record.state.metadata.get("subject_id", "")),
            "condition": record.condition,
            "observation_id": record.observation_id,
        },
    )


def subject_groups(records) -> list[LongitudinalGroup]:
    by: dict[str, list] = defaultdict(list)
    for record in records:
        by[str(record.state.metadata.get("subject_id"))].append(record)
    groups: list[LongitudinalGroup] = []
    for subject, rows in sorted(by.items()):
        ordered = tuple(sorted(rows, key=lambda r: (r.time, r.observation_id)))
        groups.append(LongitudinalGroup(subject, "hypoxia_reox_course", ordered))
    return groups


def build_scenarios(hold_records) -> list[Scenario]:
    by: dict[str, list] = defaultdict(list)
    for record in hold_records:
        by[str(record.state.metadata.get("subject_id"))].append(record)
    scenarios: list[Scenario] = []
    for subject, rows in sorted(by.items()):
        rows = sorted(rows, key=lambda r: r.time)
        norm = next((r for r in rows if r.condition == "normoxia"), rows[0])
        hyp = next((r for r in rows if r.condition == "hypoxia"), rows[-1])
        domains = dv(hyp.state.domain_scores)
        scenarios.append(
            Scenario(
                scenario_id=f"CVX-GSE144424-{subject}-hypoxia",
                version="0.1.0",
                name=f"GSE144424 subject {subject} hypoxia",
                target_model="human_iPSC_derived_cardiac_tissue",
                evidence_tier=EvidenceTier.OBSERVED,
                confidence=Confidence.MODERATE,
                phenotype_domains=domains,
                temporal_profile=(
                    ScenarioState("normoxia", 0.0, dv(norm.state.domain_scores)),
                    ScenarioState("hypoxia", 6.0, domains),
                ),
                provenance_sources=("GSE144424",),
                provenance_transformations=("ensembl_module_score", "subject_collapse"),
                ood_status="held_out_novel",
            )
        )
    return scenarios


def condition_classification(collapsed) -> dict:
    """Class-aware k-fold centroid classification of condition labels."""
    states = [dict(r.state.domain_scores) for r in collapsed]
    labels = [r.condition for r in collapsed]
    counts: dict[str, int] = defaultdict(int)
    for lab in labels:
        counts[lab] += 1
    k = min(5, min(counts.values()))
    result = cross_validate_centroid(states, labels, k=k, model_name="centroid-condition")
    return {
        "model": "centroid",
        "k_folds": k,
        "n_samples": len(states),
        "label_counts": dict(sorted(counts.items())),
        "features": sorted(states[0].keys()) if states else [],
        "mean_accuracy": float(result.mean_accuracy),
        "mean_balanced_accuracy": float(result.mean_balanced_accuracy),
        "mean_macro_f1": float(result.mean_macro_f1),
        "fold_accuracies": [float(f.accuracy) for f in result.folds],
        "fold_macro_f1": [float(f.macro_f1) for f in result.folds],
    }


def main() -> int:
    if not COUNTS.is_file():
        raise SystemExit(f"missing {COUNTS}")
    digest = _sha256(COUNTS)
    if digest != EXPECTED_SHA:
        raise SystemExit(f"SHA mismatch: {digest}")

    matrix = read_geo_counts(COUNTS)
    metadata = parse_gse144424_count_metadata(matrix.sample_ids)
    config = ModuleScoreConfig(domain_gene_sets=read_ensembl_modules(MODULES), minimum_genes=3)
    records = score_count_modules(matrix, metadata, config)
    collapsed = list(collapse_subject_replicates(records))

    held_set = set(HELD_OUT)
    dev = [r for r in collapsed if str(r.state.metadata.get("subject_id")) not in held_set]
    hold = [r for r in collapsed if str(r.state.metadata.get("subject_id")) in held_set]

    baseline_rec = next(r for r in dev if r.condition == "normoxia")
    baseline = state_from_record(baseline_rec, split="development")
    known = [state_from_record(r, split="development") for r in dev if r.condition == "normoxia"]
    scenarios = build_scenarios(hold)
    dev_groups = subject_groups(dev)
    hold_groups = subject_groups(hold)

    run = run_validated_benchmark(
        scenarios,
        baseline=baseline,
        known_states=known,
        development_groups=dev_groups,
        held_out_groups=hold_groups,
        name="gse144424-validated-heldout",
        version="0.1.0",
    )

    scenario_scores = []
    for item in run.benchmark.results:
        entry = {
            "scenario_id": item.scenario_id,
            "status": item.status,
            "issues": list(item.issues),
        }
        if item.score is not None:
            entry["overall_abnormality"] = float(item.score.overall_abnormality)
            entry["overall_novelty"] = float(item.score.overall_novelty)
            entry["attribution_coverage"] = float(item.score.attribution_coverage)
            entry["modality_scores"] = [
                {
                    "modality": m.modality,
                    "abnormality": float(m.abnormality),
                    "novelty": float(m.novelty),
                    "available": bool(m.available),
                }
                for m in item.score.modality_scores
            ]
        scenario_scores.append(entry)

    clf = condition_classification(collapsed)

    report = {
        "report_version": "0.1.0",
        "status": "real_data_validated_benchmark_complete",
        "dataset_id": "GSE144424",
        "source_sha256": digest,
        "split": {
            "held_out_subjects": list(HELD_OUT),
            "development_subject_count": len(dev_groups),
            "held_out_subject_count": len(hold_groups),
            "development_normoxia_reference_states": len(known),
            "policy": "subject-level holdout before scenario construction and surrogate validation",
        },
        "validated_benchmark": {
            "name": "gse144424-validated-heldout",
            "clean_split": run.surrogate_validation.clean_split,
            "suite_summary": report_summary(run.benchmark),
            "surrogate_summary": dict(run.surrogate_validation.summary),
            "scenario_scores": scenario_scores,
            "validation_policy": dict(run.validation_policy),
        },
        "condition_classification": clf,
        "interpretation": {
            "benchmark_layer": (
                "Held-out subject hypoxia scenarios are scored against development normoxia "
                "references. Omics abnormality is expected; imaging/functional modalities are "
                "empty so their novelty flags reflect absence of those channels."
            ),
            "surrogate_layer": (
                "Domain MAE and temporal similarity compare scenario phenotype profiles to "
                "disjoint held-out longitudinal groups. clean_split=true means no subject ID overlap."
            ),
            "classification_layer": (
                "Centroid k-fold classification of condition labels from domain scores is a "
                "transparent baseline, not a clinical predictor."
            ),
            "limitations": [
                "Omics-only; no imaging or functional measurements in GSE144424.",
                "Three held-out subjects only for the validated-benchmark scenarios.",
                "Condition classification is not subject-stratified LOSO (uses class-aware k-fold).",
            ],
        },
    }

    out = REPORTS / "GSE144424_real_validated_benchmark_v0.1.json"
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "clean_split": report["validated_benchmark"]["clean_split"],
        "suite": report["validated_benchmark"]["suite_summary"],
        "surrogate": report["validated_benchmark"]["surrogate_summary"],
        "classification_mean_accuracy": clf.get("mean_accuracy"),
        "classification_mean_macro_f1": clf.get("mean_macro_f1"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
