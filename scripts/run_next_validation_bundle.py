#!/usr/bin/env python3
"""Next validation bundle:

1. Subject-stratified LOSO condition classification (stricter than class k-fold)
2. GSE144423 ATAC multi-modal alignment + global accessibility consistency
3. Frozen content-hashed benchmark suite for regression CI

Primary LOSO metrics use within-subject delta features (condition - own normoxia).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

from cardivex.calibration_runner import build_development_calibration
from cardivex.data_plan import build_analysis_plan
from cardivex.experiments import fit_centroid_model, predict_with_model
from cardivex.features import CardiacState, ModalityVector
from cardivex.frozen_benchmark import build_frozen_benchmark, validate_frozen_benchmark_against_groups
from cardivex.geo_counts import (
    ModuleScoreConfig,
    parse_gse144424_count_metadata,
    read_geo_counts,
    score_count_modules,
)
from cardivex.longitudinal import collapse_subject_replicates, group_longitudinal_records

ROOT = Path(__file__).resolve().parents[1]
RNA_COUNTS = ROOT / "data" / "GSE144424_Counts_RNA_MCW_NEB.txt.gz"
ATAC_COUNTS = ROOT / "data" / "GSE144423_Counts_ATAC_MCW_NEB.txt.gz"
MODULES = ROOT / "configs" / "gse144424_ensembl_modules.yaml"
REPORTS = ROOT / "reports"

RNA_SHA = "cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c"
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


def load_rna():
    digest = _sha256(RNA_COUNTS)
    if digest != RNA_SHA:
        raise ValueError(f"RNA SHA mismatch: {digest}")
    matrix = read_geo_counts(RNA_COUNTS)
    metadata = parse_gse144424_count_metadata(matrix.sample_ids)
    config = ModuleScoreConfig(domain_gene_sets=read_ensembl_modules(MODULES), minimum_genes=3)
    records = score_count_modules(matrix, metadata, config)
    collapsed = list(collapse_subject_replicates(records))
    return records, collapsed, digest


def subject_loso_classification(collapsed) -> dict:
    """Primary: within-subject delta features (subtract own normoxia)."""
    by_subject: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for record in collapsed:
        sid = str(record.state.metadata.get("subject_id"))
        by_subject[sid][record.condition] = {
            d: float(v) for d, v in record.state.domain_scores.items()
        }

    features = sorted(collapsed[0].state.domain_scores.keys())
    subjects = sorted(by_subject)

    def run(mode: str) -> dict:
        folds = []
        all_true: list[str] = []
        all_pred: list[str] = []
        for hold in subjects:
            train_states, train_labels, test_states, test_labels = [], [], [], []
            for subject, conds in by_subject.items():
                if "normoxia" not in conds:
                    continue
                base = conds["normoxia"]
                for cond, scores in conds.items():
                    if mode == "delta":
                        vec = {d: scores[d] - base[d] for d in features}
                    else:
                        vec = dict(scores)
                    if subject == hold:
                        test_states.append(vec)
                        test_labels.append(cond)
                    else:
                        train_states.append(vec)
                        train_labels.append(cond)
            if not test_states or len(set(train_labels)) < 2:
                continue
            model = fit_centroid_model(train_states, train_labels, feature_names=features)
            preds = [str(p.label) for p in predict_with_model(model, test_states)]
            acc = sum(t == p for t, p in zip(test_labels, preds)) / len(test_labels)
            folds.append({"held_out_subject": hold, "n_test": len(test_labels), "accuracy": acc})
            all_true.extend(test_labels)
            all_pred.extend(preds)
        overall = sum(t == p for t, p in zip(all_true, all_pred)) / len(all_true)
        labels = sorted(set(all_true) | set(all_pred))
        f1s = []
        per_class = {}
        for lab in labels:
            tp = sum(1 for t, p in zip(all_true, all_pred) if t == lab and p == lab)
            fp = sum(1 for t, p in zip(all_true, all_pred) if t != lab and p == lab)
            fn = sum(1 for t, p in zip(all_true, all_pred) if t == lab and p != lab)
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
            f1s.append(f1)
            per_class[lab] = {
                "precision": prec,
                "recall": rec,
                "f1": f1,
                "support": sum(1 for t in all_true if t == lab),
            }
        return {
            "feature_mode": mode,
            "overall_accuracy": overall,
            "macro_f1": statistics.fmean(f1s) if f1s else 0.0,
            "mean_fold_accuracy": statistics.fmean(f["accuracy"] for f in folds) if folds else 0.0,
            "per_class": per_class,
            "fold_accuracies": [f["accuracy"] for f in folds],
            "folds": folds,
        }

    absolute = run("absolute")
    delta = run("delta")
    return {
        "method": "leave_one_subject_out_centroid",
        "n_subjects": len(subjects),
        "n_samples": 60,
        "features": features,
        "feature_contract": (
            "Primary metrics use within-subject delta (condition - own normoxia). "
            "Absolute scores retained for comparison only."
        ),
        "overall_accuracy": delta["overall_accuracy"],
        "macro_f1": delta["macro_f1"],
        "mean_fold_accuracy": delta["mean_fold_accuracy"],
        "per_class": delta["per_class"],
        "fold_accuracies": delta["fold_accuracies"],
        "folds": delta["folds"],
        "absolute_baseline": {
            "overall_accuracy": absolute["overall_accuracy"],
            "macro_f1": absolute["macro_f1"],
        },
        "delta_primary": {
            "overall_accuracy": delta["overall_accuracy"],
            "macro_f1": delta["macro_f1"],
        },
    }


def parse_atac_column(col: str) -> tuple[str, str, float]:
    m = re.match(r"^H(\d+)([ABCD])$", col)
    if not m:
        raise ValueError(f"unrecognized ATAC column: {col}")
    subject, letter = m.group(1), m.group(2)
    time_map = {"A": 0.0, "B": 6.0, "C": 12.0, "D": 30.0}
    cond_map = {"A": "normoxia", "B": "hypoxia", "C": "reoxygenation_1", "D": "reoxygenation_2"}
    return subject, cond_map[letter], time_map[letter]


def atac_sample_accessibility(path: Path) -> tuple[str, dict[str, dict]]:
    digest = _sha256(path)
    import csv
    import gzip

    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        sample_start = 6 if len(header) > 6 and header[5].lower() == "length" else 1
        sample_ids = header[sample_start:]
        totals = [0.0] * len(sample_ids)
        peak_sums = [0.0] * len(sample_ids)
        n_peaks = 0
        for row in reader:
            if not row:
                continue
            values = [float(x) for x in row[sample_start:]]
            if len(values) != len(sample_ids):
                raise ValueError("ATAC row width mismatch")
            for i, v in enumerate(values):
                if v < 0:
                    raise ValueError("negative ATAC count")
                totals[i] += v
                peak_sums[i] += v
            n_peaks += 1

    samples = {}
    for i, sid in enumerate(sample_ids):
        subject, condition, time = parse_atac_column(sid)
        mean_count = peak_sums[i] / max(n_peaks, 1)
        cpm = 0.0 if totals[i] <= 0 else (peak_sums[i] / totals[i]) * 1_000_000.0
        samples[sid] = {
            "subject_id": subject,
            "condition": condition,
            "time": time,
            "n_peaks": n_peaks,
            "library_size": totals[i],
            "mean_count": mean_count,
            "log1p_mean_count": math.log1p(mean_count),
            "log1p_total_cpm_proxy": math.log1p(cpm),
        }
    return digest, samples


def rna_atac_consistency(collapsed, atac_samples: dict) -> dict:
    atac_index = {}
    for sid, meta in atac_samples.items():
        atac_index[(meta["subject_id"], meta["condition"])] = (sid, meta)

    pairs = []
    for record in collapsed:
        subject = str(record.state.metadata.get("subject_id"))
        key = (subject, record.condition)
        if key not in atac_index:
            continue
        sid, ameta = atac_index[key]
        pairs.append(
            {
                "subject_id": subject,
                "condition": record.condition,
                "rna_observation_id": record.observation_id,
                "atac_sample_id": sid,
                "rna_domain_mean": statistics.fmean(record.state.domain_scores.values()),
                "rna_hypoxia": float(record.state.domain_scores.get("hypoxia_response", 0.0)),
                "atac_log1p_mean_count": ameta["log1p_mean_count"],
            }
        )

    def pearson(xs, ys):
        if len(xs) < 3:
            return None
        mx, my = statistics.fmean(xs), statistics.fmean(ys)
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        deny = math.sqrt(sum((y - my) ** 2 for y in ys))
        if denx == 0 or deny == 0:
            return None
        return num / (denx * deny)

    rna_mean = [p["rna_domain_mean"] for p in pairs]
    rna_hyp = [p["rna_hypoxia"] for p in pairs]
    atac = [p["atac_log1p_mean_count"] for p in pairs]
    return {
        "matched_pairs": len(pairs),
        "rna_samples_unmatched": sum(
            1 for r in collapsed
            if (str(r.state.metadata.get("subject_id")), r.condition) not in atac_index
        ),
        "atac_samples_total": len(atac_samples),
        "pearson_rna_domain_mean_vs_atac": pearson(rna_mean, atac),
        "pearson_rna_hypoxia_vs_atac": pearson(rna_hyp, atac),
        "limitation": (
            "ATAC matrix rows are genomic peaks (chr_start_end), not genes. "
            "Global accessibility scalars only; peak-to-gene module scoring not applied."
        ),
    }


def build_frozen_suite(records) -> dict:
    collapsed = list(collapse_subject_replicates(records))
    adjusted = []
    for record in collapsed:
        subject = str(record.state.metadata.get("subject_id"))
        meta = dict(record.state.metadata)
        meta["experimental_unit_id"] = subject
        meta["original_condition"] = record.condition
        state = CardiacState(
            domain_scores=dict(record.state.domain_scores),
            omics=record.state.omics or ModalityVector("omics", {"rna_module_features": 1.0}),
            time=record.time,
            metadata=meta,
        )
        adjusted.append(
            type(record)(
                observation_id=record.observation_id,
                dataset_id=record.dataset_id,
                condition="hypoxia_reox_course",
                time=record.time,
                state=state,
                available_modalities=record.available_modalities,
                source_ref=record.source_ref,
            )
        )

    try:
        plan = build_analysis_plan(adjusted, expected_times=(0.0, 6.0, 12.0, 30.0), min_holdout_groups=3)
        artifact = build_development_calibration(adjusted, plan)
        held_ids = set(artifact.held_out_group_ids)
        specs = [(f"CVX-FROZEN-GSE144424-{i:02d}", f"frozen hypoxia_reox challenge {i}") for i in range(1, 6)]
        frozen = build_frozen_benchmark(
            artifact,
            condition="hypoxia_reox_course",
            scenario_specs=specs,
            target_model="human_iPSC_derived_cardiac_tissue",
            seed=0,
        )
        scenario_ids = list(frozen.scenario_ids)
        cal_id = frozen.calibration_artifact_id
        groups = group_longitudinal_records(adjusted)
        hold_groups = [g for g in groups if g.group_id in held_ids]
        validations = validate_frozen_benchmark_against_groups(frozen, artifact, hold_groups) if hold_groups else ()
        val_summary = []
        for v in validations:
            entry = {"scenario_id": getattr(v, "scenario_id", None)}
            for attr in ("domain_mae", "mean_domain_mae", "temporal_similarity"):
                if hasattr(v, attr):
                    entry[attr] = float(getattr(v, attr))
            val_summary.append(entry)
        status, error = "ok", None
    except Exception as exc:
        scenario_ids, cal_id, held_ids, val_summary = [], None, set(), []
        status, error, artifact = "partial", f"{type(exc).__name__}: {exc}", None

    return {
        "status": status,
        "error": error,
        "calibration_artifact_id": cal_id if cal_id else (artifact.artifact_id if artifact else None),
        "held_out_group_ids": sorted(held_ids),
        "development_record_count": len(artifact.development_record_ids) if artifact else 0,
        "excluded_record_count": len(artifact.excluded_record_ids) if artifact else 0,
        "scenario_ids": scenario_ids,
        "frozen_validation": val_summary,
        "manifest_name": "cardivex-frozen-challenge-suite",
        "manifest_version": "0.5.0",
    }


def main() -> int:
    if not RNA_COUNTS.is_file():
        raise SystemExit(f"missing {RNA_COUNTS}")
    records, collapsed, rna_sha = load_rna()
    print(f"RNA: {len(records)} raw, {len(collapsed)} collapsed")

    loso = subject_loso_classification(collapsed)
    print(f"LOSO accuracy={loso['overall_accuracy']:.4f} macro_f1={loso['macro_f1']:.4f}")

    atac_block = {"status": "skipped", "reason": "ATAC matrix not present"}
    if ATAC_COUNTS.is_file():
        atac_sha, atac_samples = atac_sample_accessibility(ATAC_COUNTS)
        consistency = rna_atac_consistency(collapsed, atac_samples)
        atac_block = {
            "status": "ok",
            "dataset_id": "GSE144423",
            "source_file": ATAC_COUNTS.name,
            "source_sha256": atac_sha,
            "n_samples": len(atac_samples),
            "consistency": consistency,
            "methylation_note": "GSE144425 EPIC ~1.1GB not downloaded; ATAC 9.9MB used.",
        }
        print(f"ATAC: {len(atac_samples)} samples, matched={consistency['matched_pairs']}")

    frozen = build_frozen_suite(records)
    print(f"Frozen: status={frozen['status']} artifact={frozen['calibration_artifact_id']}")

    report = {
        "report_version": "0.2.0",
        "status": "next_validation_bundle_complete",
        "rna_source_sha256": rna_sha,
        "subject_loso_classification": loso,
        "atac_multimodal": atac_block,
        "frozen_benchmark": frozen,
        "interpretation": {
            "loso": "Primary accuracy uses within-subject delta features under subject LOSO.",
            "atac": "ATAC global accessibility aligned to RNA by subject x condition.",
            "frozen": "Calibration artifact is content-hashed for CI regression.",
        },
    }
    out = REPORTS / "GSE144424_next_validation_bundle_v0.1.json"
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")

    summary = {
        "status": "ok",
        "loso_accuracy": loso["overall_accuracy"],
        "loso_macro_f1": loso["macro_f1"],
        "atac_matched_pairs": atac_block.get("consistency", {}).get("matched_pairs"),
        "frozen_artifact_id": frozen.get("calibration_artifact_id"),
        "frozen_status": frozen.get("status"),
        "rna_sha256": rna_sha,
    }
    (REPORTS / "NEXT_BUNDLE_SUMMARY_2026-08-30.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
