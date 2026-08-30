#!/usr/bin/env python3
"""External recovery-gene validation (GSE117192) + peak-to-gene ATAC (GSE144423)."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

from cardivex.experiments import fit_centroid_model, predict_with_model

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DATA = ROOT / "data"

GSE117192 = DATA / "GSE117192_Counts_RNA_MCWard.txt.gz"
GSE144424 = DATA / "GSE144424_Counts_RNA_MCW_NEB.txt.gz"
ATAC = DATA / "GSE144423_Counts_ATAC_MCW_NEB.txt.gz"
COORDS = DATA / "module_gene_coords_grch38.tsv"
RECOVERY_CFG = ROOT / "configs" / "gse144424_recovery_module_v0.1.yaml"
BASE_CFG = ROOT / "configs" / "gse144424_ensembl_modules.yaml"

GSE117192_SHA = "b761607e773eea15d8070b533b78553a6b15959e8f8932ac937b63c12ca55dd1"
ATAC_WINDOW = 50_000


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ensembl_list(path: Path) -> dict[str, tuple[str, ...]]:
    text = path.read_text(encoding="utf-8")
    modules: dict[str, tuple[str, ...]] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if m:
            current = m.group(1)
            continue
        e = re.match(r"^    ensembl:\s*\[(.*)\]\s*$", line)
        if e and current:
            vals = [x.strip().strip("'\"") for x in e.group(1).split(",") if x.strip()]
            modules[current] = tuple(vals)
    if not modules and "ENSG" in text:
        modules["recovery_trajectory"] = tuple(re.findall(r"ENSG\d+", text))
    return modules


def load_count_matrix(path: Path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        sample_ids = header[1:]
        counts = {}
        for row in reader:
            if not row:
                continue
            gid = row[0].split(".")[0]
            vals = [float(x) for x in row[1 : 1 + len(sample_ids)]]
            if len(vals) == len(sample_ids):
                counts[gid] = vals
    return sample_ids, list(counts), counts


def parse_condition_subject(sample: str):
    m = re.match(r"^([HC])(\d+)R?_?([ABCD])$", sample)
    if not m:
        return None
    letter = m.group(3)
    cond = {"A": "normoxia", "B": "hypoxia", "C": "reoxygenation_1", "D": "reoxygenation_2"}[letter]
    return m.group(2), cond


def module_log1p_cpm(counts, genes, sample_index, lib_size):
    vals = []
    for g in genes:
        if g not in counts:
            continue
        cpm = counts[g][sample_index] / lib_size * 1e6 if lib_size else 0.0
        vals.append(math.log1p(cpm))
    return statistics.fmean(vals) if vals else 0.0


def score_recovery_external() -> dict:
    digest = _sha256(GSE117192)
    if digest != GSE117192_SHA:
        raise ValueError(f"SHA mismatch: {digest}")
    sample_ids, _, counts = load_count_matrix(GSE117192)
    recovery = parse_ensembl_list(RECOVERY_CFG)["recovery_trajectory"]
    present = sum(1 for g in recovery if g in counts)
    human_idx = [i for i, s in enumerate(sample_ids) if s.startswith("H")]
    lib = [0.0] * len(sample_ids)
    for g, row in counts.items():
        for i in human_idx:
            lib[i] += row[i]
    by_subj = defaultdict(dict)
    for i in human_idx:
        parsed = parse_condition_subject(sample_ids[i])
        if not parsed:
            continue
        sid, cond = parsed
        by_subj[sid][cond] = module_log1p_cpm(counts, recovery, i, lib[i])
    subjects = sorted(
        s for s, c in by_subj.items()
        if "normoxia" in c and "reoxygenation_1" in c and "reoxygenation_2" in c
    )
    yt, yp = [], []
    for hold in subjects:
        trx, try_, tex, tey = [], [], [], []
        for sid in subjects:
            base = by_subj[sid]["normoxia"]
            for cond in ("reoxygenation_1", "reoxygenation_2"):
                feat = {"recovery_dn": by_subj[sid][cond] - base}
                if "hypoxia" in by_subj[sid]:
                    feat["recovery_dh"] = by_subj[sid][cond] - by_subj[sid]["hypoxia"]
                feat["recovery_dr1"] = (
                    by_subj[sid][cond] - by_subj[sid]["reoxygenation_1"]
                    if cond == "reoxygenation_2" and "reoxygenation_1" in by_subj[sid]
                    else 0.0
                )
                if sid == hold:
                    tex.append(feat); tey.append(cond)
                else:
                    trx.append(feat); try_.append(cond)
        if not tex or len(set(try_)) < 2:
            continue
        model = fit_centroid_model(trx, try_)
        preds = [str(p.label) for p in predict_with_model(model, tex)]
        yt.extend(tey); yp.extend(preds)
    acc = sum(t == p for t, p in zip(yt, yp)) / len(yt) if yt else 0.0
    traj = {}
    for cond in ("normoxia", "hypoxia", "reoxygenation_1", "reoxygenation_2"):
        vals = [by_subj[s][cond] for s in subjects if cond in by_subj[s]]
        traj[cond] = statistics.fmean(vals) if vals else None
    paired = [
        by_subj[s]["reoxygenation_2"] - by_subj[s]["reoxygenation_1"]
        for s in subjects
        if "reoxygenation_1" in by_subj[s] and "reoxygenation_2" in by_subj[s]
    ]
    return {
        "dataset": "GSE117192",
        "source_sha256": digest,
        "species_filter": "human_only",
        "n_human_subjects_with_full_course": len(subjects),
        "recovery_genes_requested": len(recovery),
        "recovery_genes_present": present,
        "mean_recovery_module_by_condition": traj,
        "mean_paired_reox2_minus_reox1": statistics.fmean(paired) if paired else None,
        "loso_reox1_vs_reox2_accuracy": acc,
        "loso_n": len(yt),
        "note": "Independent human iPSC-CM hypoxia-reox (Ward & Gilad 2019); genes selected on GSE144424 only.",
    }


def load_gene_coords():
    coords = {}
    with COORDS.open() as f:
        next(f)
        for line in f:
            gid, chrom, start, end, _ = line.strip().split("\t")
            coords[gid] = (chrom, int(start), int(end))
    return coords


def peak_to_gene_atac() -> dict:
    if not ATAC.is_file():
        return {"status": "skipped", "reason": "ATAC missing"}
    coords = load_gene_coords()
    recovery = parse_ensembl_list(RECOVERY_CFG).get("recovery_trajectory", ())
    base = parse_ensembl_list(BASE_CFG)
    all_modules = dict(base)
    all_modules["recovery_trajectory"] = recovery
    by_chrom = defaultdict(list)
    for gid, (chrom, start, end) in coords.items():
        by_chrom[chrom].append((start - ATAC_WINDOW, end + ATAC_WINDOW, gid))
    for chrom in by_chrom:
        by_chrom[chrom].sort()

    def genes_for_peak(chrom, start, end):
        hits = []
        for gs, ge, gid in by_chrom.get(chrom, ()):
            if ge < start:
                continue
            if gs > end:
                break
            if not (end < gs or start > ge):
                hits.append(gid)
        return hits

    with gzip.open(ATAC, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        sample_start = 6 if header[5].lower() == "length" else 1
        sample_ids = header[sample_start:]
        n_s = len(sample_ids)
        gene_sum = {g: [0.0] * n_s for g in coords}
        gene_npeak = {g: 0 for g in coords}
        n_peaks = n_assigned = 0
        for row in reader:
            if not row:
                continue
            chrom, start, end = row[1], int(row[2]), int(row[3])
            if not chrom.startswith("chr"):
                chrom = "chr" + chrom
            hits = genes_for_peak(chrom, start, end)
            values = [float(x) for x in row[sample_start:]]
            n_peaks += 1
            if not hits:
                continue
            n_assigned += 1
            for gid in hits:
                gene_npeak[gid] += 1
                for i, v in enumerate(values):
                    gene_sum[gid][i] += v

    lib = [0.0] * n_s
    for row in gene_sum.values():
        for i, v in enumerate(row):
            lib[i] += v

    sample_meta = {}
    for sid in sample_ids:
        m = re.match(r"^H(\d+)([ABCD])$", sid)
        if m:
            sample_meta[sid] = (
                m.group(1),
                {"A": "normoxia", "B": "hypoxia", "C": "reoxygenation_1", "D": "reoxygenation_2"}[m.group(2)],
            )

    atac_by_sc = {}
    for i, sid in enumerate(sample_ids):
        if sid not in sample_meta:
            continue
        subject, cond = sample_meta[sid]
        scores = {}
        for domain, genes in all_modules.items():
            vals = []
            for g in genes:
                if g not in gene_sum or gene_npeak[g] == 0:
                    continue
                cpm = gene_sum[g][i] / lib[i] * 1e6 if lib[i] else 0.0
                vals.append(math.log1p(cpm))
            scores[domain] = statistics.fmean(vals) if vals else 0.0
        atac_by_sc[(subject, cond)] = scores

    from cardivex.geo_counts import (
        parse_gse144424_count_metadata,
        read_geo_counts,
    )

    matrix = read_geo_counts(GSE144424)
    meta = parse_gse144424_count_metadata(matrix.sample_ids)
    modules_for_rna = dict(base)
    modules_for_rna["recovery_trajectory"] = recovery
    n_samp = len(matrix.sample_ids)
    lib_rna = [0.0] * n_samp
    for gi in range(len(matrix.gene_ids)):
        row = matrix.counts[gi]
        for si in range(n_samp):
            lib_rna[si] += row[si]
    gene_index = {g: i for i, g in enumerate(matrix.gene_ids)}
    rna_by_sc = defaultdict(list)
    for si, m in enumerate(meta):
        scores = {}
        for domain, genes in modules_for_rna.items():
            vals = []
            for g in genes:
                gi = gene_index.get(g)
                if gi is None:
                    continue
                cpm = matrix.counts[gi][si] / lib_rna[si] * 1e6 if lib_rna[si] else 0.0
                vals.append(math.log1p(cpm))
            scores[domain] = statistics.fmean(vals) if vals else 0.0
        rna_by_sc[(m.subject_id, m.condition)].append(scores)
    rna_collapsed = {
        k: {d: statistics.fmean(r[d] for r in rows) for d in modules_for_rna}
        for k, rows in rna_by_sc.items()
    }

    correlations = {}
    matched = 0
    for key, rna_scores in rna_collapsed.items():
        if key not in atac_by_sc:
            continue
        matched += 1
        for domain in modules_for_rna:
            correlations.setdefault(domain, []).append((rna_scores[domain], atac_by_sc[key][domain]))

    def pearson(pairs):
        if len(pairs) < 5:
            return None
        xs, ys = [a for a, _ in pairs], [b for _, b in pairs]
        mx, my = statistics.fmean(xs), statistics.fmean(ys)
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        deny = math.sqrt(sum((y - my) ** 2 for y in ys))
        if denx == 0 or deny == 0:
            return None
        return num / (denx * deny)

    domain_r = {d: pearson(pairs) for d, pairs in correlations.items()}

    by_subj_atac = defaultdict(dict)
    for (sid, cond), scores in atac_by_sc.items():
        by_subj_atac[sid][cond] = scores.get("recovery_trajectory", 0.0)
    subjects = sorted(
        s for s, c in by_subj_atac.items()
        if "normoxia" in c and "reoxygenation_1" in c and "reoxygenation_2" in c
    )
    yt, yp = [], []
    for hold in subjects:
        trx, try_, tex, tey = [], [], [], []
        for sid in subjects:
            base = by_subj_atac[sid]["normoxia"]
            for cond in ("reoxygenation_1", "reoxygenation_2"):
                feat = {"atac_rec_dn": by_subj_atac[sid][cond] - base}
                if sid == hold:
                    tex.append(feat); tey.append(cond)
                else:
                    trx.append(feat); try_.append(cond)
        if not tex or len(set(try_)) < 2:
            continue
        model = fit_centroid_model(trx, try_)
        preds = [str(p.label) for p in predict_with_model(model, tex)]
        yt.extend(tey); yp.extend(preds)
    atac_reox_acc = sum(t == p for t, p in zip(yt, yp)) / len(yt) if yt else 0.0

    return {
        "status": "ok",
        "dataset_atac": "GSE144423",
        "peak_to_gene_window_bp": ATAC_WINDOW,
        "n_peaks_total": n_peaks,
        "n_peaks_assigned_to_module_genes": n_assigned,
        "module_genes_with_coords": len(coords),
        "module_genes_with_peaks": sum(1 for n in gene_npeak.values() if n > 0),
        "matched_rna_atac_pairs": matched,
        "pearson_rna_vs_atac_by_domain": domain_r,
        "atac_loso_reox1_vs_reox2_accuracy": atac_reox_acc,
        "limitation": "Gene body +/-50kb peak-to-gene; bulk ATAC weakly tracks recovery RNA here.",
    }


def main() -> int:
    external = score_recovery_external()
    print(f"External reox_acc={external['loso_reox1_vs_reox2_accuracy']:.3f}")
    atac = peak_to_gene_atac()
    print(f"ATAC recovery r={atac.get('pearson_rna_vs_atac_by_domain', {}).get('recovery_trajectory')}")
    report = {
        "report_version": "0.1.0",
        "status": "external_and_atac_complete",
        "external_recovery_validation": external,
        "peak_to_gene_atac": atac,
        "summary": {
            "external_reox_loso_accuracy": external["loso_reox1_vs_reox2_accuracy"],
            "external_mean_reox2_minus_reox1": external["mean_paired_reox2_minus_reox1"],
            "atac_recovery_rna_correlation": atac.get("pearson_rna_vs_atac_by_domain", {}).get("recovery_trajectory"),
            "atac_reox_loso_accuracy": atac.get("atac_loso_reox1_vs_reox2_accuracy"),
        },
    }
    out = REPORTS / "GSE144424_external_and_atac_validation_v0.1.json"
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
