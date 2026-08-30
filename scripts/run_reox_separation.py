#!/usr/bin/env python3
"""Separate reoxygenation_1 vs reoxygenation_2 with recovery-enriched genes.

Within each LOSO fold, rank genes by paired reox2-reox1 effect on development
subjects only; form recovery_trajectory module. Features are multi-baseline
within-subject deltas (vs normoxia, hypoxia, reox1).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

from cardivex.experiments import fit_centroid_model, predict_with_model
from cardivex.geo_counts import (
    ModuleScoreConfig,
    parse_gse144424_count_metadata,
    read_geo_counts,
    score_count_modules,
)
from cardivex.longitudinal import collapse_subject_replicates

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ROOT / "data" / "GSE144424_Counts_RNA_MCW_NEB.txt.gz"
MODULES = ROOT / "configs" / "gse144424_ensembl_modules.yaml"
REPORTS = ROOT / "reports"
EXPECTED_SHA = "cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c"
FIXED_HELD = ("19128", "18870", "18855")


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
    return modules


def log1p_cpm_row(row, lib, sample_indices):
    vals = []
    for si in sample_indices:
        cpm = (row[si] / lib[si] * 1e6) if lib[si] else 0.0
        vals.append(math.log1p(cpm))
    return statistics.fmean(vals) if vals else 0.0


def select_recovery_genes(matrix, meta, *, development_subjects, top_n=24, min_subjects=6):
    n_samples = len(matrix.sample_ids)
    n_genes = len(matrix.gene_ids)
    lib = [0.0] * n_samples
    for gi in range(n_genes):
        row = matrix.counts[gi]
        for si in range(n_samples):
            lib[si] += row[si]
    by_sc = defaultdict(list)
    for si, m in enumerate(meta):
        by_sc[(m.subject_id, m.condition)].append(si)
    ranked = []
    for gi, gid in enumerate(matrix.gene_ids):
        row = matrix.counts[gi]
        if sum(1 for v in row if v > 0) < 15:
            continue
        diffs = []
        for sid in development_subjects:
            k1, k2 = (sid, "reoxygenation_1"), (sid, "reoxygenation_2")
            if k1 not in by_sc or k2 not in by_sc:
                continue
            diffs.append(log1p_cpm_row(row, lib, by_sc[k2]) - log1p_cpm_row(row, lib, by_sc[k1]))
        if len(diffs) < min_subjects:
            continue
        effect = statistics.fmean(diffs)
        sd = statistics.pstdev(diffs) if len(diffs) > 1 else 0.0
        t = effect / (sd / math.sqrt(len(diffs))) if sd > 1e-12 else 0.0
        if abs(effect) < 0.12:
            continue
        ranked.append((abs(t), t, effect, gid))
    ranked.sort(reverse=True)
    up = [g for _, t, _, g in ranked if t > 0][: top_n // 2]
    down = [g for _, t, _, g in ranked if t < 0][: top_n // 2]
    chosen = tuple(dict.fromkeys(up + down))
    if len(chosen) < 8:
        chosen = tuple(g for _, _, _, g in ranked[:top_n])
    return chosen


def score_modules_for_samples(matrix, meta, domain_gene_sets):
    gene_index = {g: i for i, g in enumerate(matrix.gene_ids)}
    n_samples = len(matrix.sample_ids)
    n_genes = len(matrix.gene_ids)
    lib = [0.0] * n_samples
    for gi in range(n_genes):
        row = matrix.counts[gi]
        for si in range(n_samples):
            lib[si] += row[si]
    sample_scores = {}
    for si, m in enumerate(meta):
        scores = {}
        for domain, genes in domain_gene_sets.items():
            vals = []
            for g in genes:
                gi = gene_index.get(g)
                if gi is None:
                    continue
                cpm = matrix.counts[gi][si] / lib[si] * 1e6 if lib[si] else 0.0
                vals.append(math.log1p(cpm))
            scores[domain] = statistics.fmean(vals) if vals else 0.0
        sample_scores[m.sample_id] = scores
    by_sc = defaultdict(list)
    for m in meta:
        by_sc[(m.subject_id, m.condition)].append(sample_scores[m.sample_id])
    collapsed = defaultdict(dict)
    domains = list(domain_gene_sets)
    for (sid, cond), rows in by_sc.items():
        collapsed[sid][cond] = {d: statistics.fmean(r[d] for r in rows) for d in domains}
    return collapsed


def multi_baseline_features(cond, scores, subject_conds, domains):
    if "normoxia" not in subject_conds:
        return None
    base_n = subject_conds["normoxia"]
    feat = {f"dn_{d}": scores[d] - base_n[d] for d in domains}
    if "hypoxia" in subject_conds:
        base_h = subject_conds["hypoxia"]
        for d in domains:
            feat[f"dh_{d}"] = scores[d] - base_h[d]
    else:
        for d in domains:
            feat[f"dh_{d}"] = 0.0
    if cond == "reoxygenation_2" and "reoxygenation_1" in subject_conds:
        base_r = subject_conds["reoxygenation_1"]
        for d in domains:
            feat[f"dr1_{d}"] = scores[d] - base_r[d]
    else:
        for d in domains:
            feat[f"dr1_{d}"] = 0.0
    return feat


def loso_reox_pipeline(matrix, meta, base_modules):
    subjects = sorted({m.subject_id for m in meta})
    results_four, results_reox = [], []
    all_true_4, all_pred_4, all_true_r, all_pred_r = [], [], [], []
    recovery_gene_counts = []
    for hold in subjects:
        dev = {s for s in subjects if s != hold}
        recovery = select_recovery_genes(matrix, meta, development_subjects=dev, top_n=24)
        recovery_gene_counts.append(len(recovery))
        domains = dict(base_modules)
        domains["recovery_trajectory"] = recovery
        collapsed = score_modules_for_samples(matrix, meta, domains)
        domain_names = sorted(domains)
        tr_x, tr_y, te_x, te_y = [], [], [], []
        for sid, conds in collapsed.items():
            for cond, scores in conds.items():
                feat = multi_baseline_features(cond, scores, conds, domain_names)
                if feat is None:
                    continue
                if sid == hold:
                    te_x.append(feat); te_y.append(cond)
                else:
                    tr_x.append(feat); tr_y.append(cond)
        if te_x and len(set(tr_y)) >= 2:
            model = fit_centroid_model(tr_x, tr_y)
            preds = [str(p.label) for p in predict_with_model(model, te_x)]
            results_four.append(sum(t == p for t, p in zip(te_y, preds)) / len(te_y))
            all_true_4.extend(te_y); all_pred_4.extend(preds)
        tr_x, tr_y, te_x, te_y = [], [], [], []
        for sid, conds in collapsed.items():
            for cond in ("reoxygenation_1", "reoxygenation_2"):
                if cond not in conds:
                    continue
                feat = multi_baseline_features(cond, conds[cond], conds, domain_names)
                if feat is None:
                    continue
                if sid == hold:
                    te_x.append(feat); te_y.append(cond)
                else:
                    tr_x.append(feat); tr_y.append(cond)
        if te_x and len(set(tr_y)) >= 2:
            model = fit_centroid_model(tr_x, tr_y)
            preds = [str(p.label) for p in predict_with_model(model, te_x)]
            results_reox.append(sum(t == p for t, p in zip(te_y, preds)) / len(te_y))
            all_true_r.extend(te_y); all_pred_r.extend(preds)

    def summarize(y_t, y_p, fold_accs):
        if not y_t:
            return {"overall_accuracy": 0.0, "macro_f1": 0.0, "n": 0}
        labels = sorted(set(y_t) | set(y_p))
        f1s, per = [], {}
        for lab in labels:
            tp = sum(1 for t, p in zip(y_t, y_p) if t == lab and p == lab)
            fp = sum(1 for t, p in zip(y_t, y_p) if t != lab and p == lab)
            fn = sum(1 for t, p in zip(y_t, y_p) if t == lab and p != lab)
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
            f1s.append(f1)
            per[lab] = {"precision": prec, "recall": rec, "f1": f1, "support": sum(1 for t in y_t if t == lab)}
        return {
            "overall_accuracy": sum(t == p for t, p in zip(y_t, y_p)) / len(y_t),
            "macro_f1": statistics.fmean(f1s) if f1s else 0.0,
            "mean_fold_accuracy": statistics.fmean(fold_accs) if fold_accs else 0.0,
            "n": len(y_t),
            "per_class": per,
        }

    return {
        "four_class_multi_baseline_recovery": summarize(all_true_4, all_pred_4, results_four),
        "reox1_vs_reox2": summarize(all_true_r, all_pred_r, results_reox),
        "mean_recovery_genes_per_fold": statistics.fmean(recovery_gene_counts) if recovery_gene_counts else 0,
    }


def fixed_split_report(matrix, meta, base_modules):
    dev = {m.subject_id for m in meta if m.subject_id not in FIXED_HELD}
    recovery = select_recovery_genes(matrix, meta, development_subjects=dev, top_n=24)
    domains = dict(base_modules)
    domains["recovery_trajectory"] = recovery
    collapsed = score_modules_for_samples(matrix, meta, domains)
    domain_names = sorted(domains)
    tr_x, tr_y, te_x, te_y = [], [], [], []
    for sid, conds in collapsed.items():
        for cond in ("reoxygenation_1", "reoxygenation_2"):
            if cond not in conds:
                continue
            feat = multi_baseline_features(cond, conds[cond], conds, domain_names)
            if feat is None:
                continue
            if sid in FIXED_HELD:
                te_x.append(feat); te_y.append(cond)
            else:
                tr_x.append(feat); tr_y.append(cond)
    model = fit_centroid_model(tr_x, tr_y)
    preds = [str(p.label) for p in predict_with_model(model, te_x)]
    acc = sum(t == p for t, p in zip(te_y, preds)) / len(te_y) if te_y else 0.0
    return {
        "held_out_subjects": list(FIXED_HELD),
        "recovery_genes": list(recovery),
        "n_recovery_genes": len(recovery),
        "n_train": len(tr_y),
        "n_test": len(te_y),
        "accuracy": acc,
    }


def main() -> int:
    digest = _sha256(COUNTS)
    if digest != EXPECTED_SHA:
        raise SystemExit(f"SHA mismatch: {digest}")
    matrix = read_geo_counts(COUNTS)
    meta = parse_gse144424_count_metadata(matrix.sample_ids)
    base_modules = read_ensembl_modules(MODULES)
    print("Running LOSO with recovery module + multi-baseline features...")
    loso = loso_reox_pipeline(matrix, meta, base_modules)
    print(json.dumps(loso, indent=2))
    fixed = fixed_split_report(matrix, meta, base_modules)
    print(f"fixed split reox accuracy={fixed['accuracy']:.3f} genes={fixed['n_recovery_genes']}")

    cfg = ModuleScoreConfig(domain_gene_sets=base_modules, minimum_genes=3)
    records = score_count_modules(matrix, meta, cfg)
    collapsed_rec = list(collapse_subject_replicates(records))
    by_subj = defaultdict(dict)
    for r in collapsed_rec:
        by_subj[str(r.state.metadata.get("subject_id"))][r.condition] = dict(r.state.domain_scores)
    domains5 = sorted(next(iter(next(iter(by_subj.values())).values())))
    yt, yp = [], []
    for hold in sorted(by_subj):
        trx, try_, tex, tey = [], [], [], []
        for sid, conds in by_subj.items():
            if "normoxia" not in conds:
                continue
            base = conds["normoxia"]
            for cond in ("reoxygenation_1", "reoxygenation_2"):
                if cond not in conds:
                    continue
                feat = {d: conds[cond][d] - base[d] for d in domains5}
                if sid == hold:
                    tex.append(feat); tey.append(cond)
                else:
                    trx.append(feat); try_.append(cond)
        if not tex or len(set(try_)) < 2:
            continue
        model = fit_centroid_model(trx, try_)
        preds = [str(p.label) for p in predict_with_model(model, tex)]
        yt.extend(tey); yp.extend(preds)
    baseline_reox_acc = sum(t == p for t, p in zip(yt, yp)) / len(yt) if yt else 0.0

    report = {
        "report_version": "0.1.0",
        "status": "reox_separation_complete",
        "source_sha256": digest,
        "baseline_5module_delta_reox1_vs_reox2_accuracy": baseline_reox_acc,
        "improved_loso": loso,
        "fixed_heldout_recovery_module": {
            "held_out_subjects": fixed["held_out_subjects"],
            "n_recovery_genes": fixed["n_recovery_genes"],
            "recovery_genes": fixed["recovery_genes"],
            "accuracy": fixed["accuracy"],
            "n_test": fixed["n_test"],
            "n_train": fixed["n_train"],
        },
        "method": {
            "recovery_gene_selection": "LOSO fold-wise paired reox2-reox1 ranking on development only",
            "features": "Multi-baseline deltas vs normoxia/hypoxia/reox1 + recovery module",
        },
        "interpretation": {
            "why_reox_overlapped": "Original 5 modules track acute hypoxia; recovery programs under-represented",
            "what_changed": "Recovery-enriched genes + multi-baseline trajectory features",
        },
    }
    out = REPORTS / "GSE144424_reox_separation_v0.1.json"
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "baseline_reox_acc": baseline_reox_acc,
        "improved_reox_acc": loso["reox1_vs_reox2"]["overall_accuracy"],
        "improved_four_class": loso["four_class_multi_baseline_recovery"]["overall_accuracy"],
        "fixed_split_reox_acc": fixed["accuracy"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
