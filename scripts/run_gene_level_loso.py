#!/usr/bin/env python3
"""Honest gene-level LOSO classification for GSE144424.

Fold-wise gene selection (paired reox2-reox1 on development only) +
per-gene multi-baseline deltas. Module means discarded gene-specific axes.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from cardivex.experiments import fit_centroid_model, predict_with_model
from cardivex.geo_counts import parse_gse144424_count_metadata, read_geo_counts

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ROOT / "data" / "GSE144424_Counts_RNA_MCW_NEB.txt.gz"
REPORTS = ROOT / "reports"
EXPECTED_SHA = "cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c"
POOL_SIZE = 400
TOP_N = 30


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    digest = _sha256(COUNTS)
    if digest != EXPECTED_SHA:
        raise SystemExit(f"SHA mismatch: {digest}")

    matrix = read_geo_counts(COUNTS)
    meta = parse_gse144424_count_metadata(matrix.sample_ids)
    n_s = len(matrix.sample_ids)
    lib = [0.0] * n_s
    for gi in range(len(matrix.gene_ids)):
        for si in range(n_s):
            lib[si] += matrix.counts[gi][si]

    by_sc: dict[tuple[str, str], list[int]] = defaultdict(list)
    for si, m in enumerate(meta):
        by_sc[(m.subject_id, m.condition)].append(si)
    subjects = sorted({m.subject_id for m in meta})

    def mean_logcpm(row, idxs):
        return statistics.fmean(
            math.log1p(row[i] / lib[i] * 1e6 if lib[i] else 0.0) for i in idxs
        )

    global_ranked = []
    for gi, gid in enumerate(matrix.gene_ids):
        row = matrix.counts[gi]
        if sum(1 for v in row if v > 0) < 15:
            continue
        diffs = []
        for sid in subjects:
            k1, k2 = (sid, "reoxygenation_1"), (sid, "reoxygenation_2")
            if k1 not in by_sc or k2 not in by_sc:
                continue
            diffs.append(mean_logcpm(row, by_sc[k2]) - mean_logcpm(row, by_sc[k1]))
        if len(diffs) < 8:
            continue
        effect = statistics.fmean(diffs)
        sd = statistics.pstdev(diffs) or 1e-9
        t = effect / (sd / math.sqrt(len(diffs)))
        if abs(effect) < 0.1:
            continue
        global_ranked.append((abs(t), gi, gid))
    global_ranked.sort(reverse=True)
    pool = global_ranked[:POOL_SIZE]
    print(f"candidate pool: {len(pool)}")

    pool_scores: dict[int, dict[str, dict[str, float]]] = {}
    for _, gi, gid in pool:
        row = matrix.counts[gi]
        by: dict[str, dict[str, float]] = {}
        for sid in subjects:
            by[sid] = {}
            for cond in ("normoxia", "hypoxia", "reoxygenation_1", "reoxygenation_2"):
                if (sid, cond) not in by_sc:
                    continue
                by[sid][cond] = mean_logcpm(row, by_sc[(sid, cond)])
        pool_scores[gi] = by

    def select_fold(dev: set[str], top_n: int = TOP_N):
        ranked = []
        for _, gi, gid in pool:
            diffs = []
            for sid in dev:
                sc = pool_scores[gi].get(sid, {})
                if "reoxygenation_1" in sc and "reoxygenation_2" in sc:
                    diffs.append(sc["reoxygenation_2"] - sc["reoxygenation_1"])
            if len(diffs) < 6:
                continue
            effect = statistics.fmean(diffs)
            sd = statistics.pstdev(diffs) or 1e-9
            t = effect / (sd / math.sqrt(len(diffs)))
            if abs(effect) < 0.1:
                continue
            ranked.append((abs(t), t, gi, gid))
        ranked.sort(reverse=True)
        up = [x for x in ranked if x[1] > 0][: top_n // 2]
        down = [x for x in ranked if x[1] < 0][: top_n // 2]
        return up + down

    yt, yp, yt_r, yp_r = [], [], [], []
    for hold in subjects:
        genes = select_fold({s for s in subjects if s != hold})
        gis = [gi for _, _, gi, _ in genes]
        gids = [gid for _, _, _, gid in genes]
        trx, try_, tex, tey = [], [], [], []
        for sid in subjects:
            if not gis or not all("normoxia" in pool_scores[gi].get(sid, {}) for gi in gis):
                continue
            for cond in ("normoxia", "hypoxia", "reoxygenation_1", "reoxygenation_2"):
                if not all(cond in pool_scores[gi].get(sid, {}) for gi in gis):
                    continue
                feat = {}
                for gi, gid in zip(gis, gids):
                    sc = pool_scores[gi][sid][cond]
                    base = pool_scores[gi][sid]["normoxia"]
                    feat[f"dn_{gid}"] = sc - base
                    if "hypoxia" in pool_scores[gi][sid]:
                        feat[f"dh_{gid}"] = sc - pool_scores[gi][sid]["hypoxia"]
                    if cond == "reoxygenation_2" and "reoxygenation_1" in pool_scores[gi][sid]:
                        feat[f"dr1_{gid}"] = sc - pool_scores[gi][sid]["reoxygenation_1"]
                if sid == hold:
                    tex.append((cond, feat))
                else:
                    trx.append((cond, feat))
        if not tex or len({c for c, _ in trx}) < 2:
            continue
        tr_x, tr_y = [f for _, f in trx], [c for c, _ in trx]
        te_x, te_y = [f for _, f in tex], [c for c, _ in tex]
        model = fit_centroid_model(tr_x, tr_y)
        preds = [str(p.label) for p in predict_with_model(model, te_x)]
        yt.extend(te_y)
        yp.extend(preds)
        tr_xr = [f for c, f in trx if c in ("reoxygenation_1", "reoxygenation_2")]
        tr_yr = [c for c, f in trx if c in ("reoxygenation_1", "reoxygenation_2")]
        te_xr = [f for c, f in tex if c in ("reoxygenation_1", "reoxygenation_2")]
        te_yr = [c for c, f in tex if c in ("reoxygenation_1", "reoxygenation_2")]
        if te_xr and len(set(tr_yr)) >= 2:
            model = fit_centroid_model(tr_xr, tr_yr)
            preds = [str(p.label) for p in predict_with_model(model, te_xr)]
            yt_r.extend(te_yr)
            yp_r.extend(preds)

    def summarize(y_t, y_p):
        acc = sum(t == p for t, p in zip(y_t, y_p)) / len(y_t) if y_t else 0.0
        per = {}
        for lab in sorted(set(y_t) | set(y_p)):
            tp = sum(1 for t, p in zip(y_t, y_p) if t == lab and p == lab)
            fp = sum(1 for t, p in zip(y_t, y_p) if t != lab and p == lab)
            fn = sum(1 for t in y_t if t == lab) - tp
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
            per[lab] = {"precision": prec, "recall": rec, "f1": f1, "support": sum(1 for t in y_t if t == lab)}
        return acc, per

    acc4, per4 = summarize(yt, yp)
    accr, perr = summarize(yt_r, yp_r)
    print(f"4-class LOSO accuracy={acc4:.3f}")
    print(f"reox LOSO accuracy={accr:.3f}")

    report = {
        "report_version": "0.3.0",
        "status": "gene_level_loso_complete",
        "source_sha256": digest,
        "four_class": {"accuracy": acc4, "per_class": per4, "n": len(yt)},
        "reox1_vs_reox2": {"accuracy": accr, "per_class": perr, "n": len(yt_r)},
        "comparison_to_module_mean": {
            "module_mean_four_class": 0.833,
            "module_mean_reox": 0.90,
            "gene_level_four_class": acc4,
            "gene_level_reox": accr,
        },
    }
    out = REPORTS / "GSE144424_gene_level_loso_v0.3.json"
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
