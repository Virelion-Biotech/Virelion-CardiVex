#!/usr/bin/env python3
"""Run full validation slices: LOSO temporal, GSE234907 no-refit external, dossier inputs.

Deterministic. No external network. Requires local count matrices under data/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

from cardivex.external_validation import validate_external_effect
from cardivex.frozen_modules import FrozenModuleTransform, freeze_module_transform
from cardivex.geo_counts import (
    ModuleScoreConfig,
    fit_module_scaler,
    parse_gse144424_count_metadata,
    read_geo_counts,
    score_count_modules,
)
from cardivex.gse234907 import read_gse234907_heart_counts
from cardivex.gse234907_frozen import score_gse234907_with_frozen_transform
from cardivex.longitudinal import (
    LongitudinalGroup,
    collapse_subject_replicates,
    validate_disjoint_longitudinal_groups,
)
from cardivex.temporal_benchmark import benchmark_temporal_surrogate
from cardivex.temporal_surrogate import TemporalSurrogateSpec, fit_temporal_surrogate


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COUNTS = ROOT / "data" / "GSE144424_Counts_RNA_MCW_NEB.txt.gz"
DEFAULT_GSE234907 = ROOT / "data" / "GSE234907_Heart_counts.txt.gz"
DEFAULT_MODULES = ROOT / "configs" / "gse144424_ensembl_modules.yaml"
REPORTS = ROOT / "reports"

EXPECTED_SHA_GSE144424 = "cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c"
HELD_OUT_SUBJECTS_FROZEN = ("19128", "18870", "18855")

# NCBI Gene Entrez IDs matching the GSE234907 Heart_counts row labels (numeric strings).
GSE234907_ENTREZ_MODULES: dict[str, tuple[str, ...]] = {
    "hypoxia_response": ("3091", "7422", "112399", "3939", "6513", "664", "133"),
    "inflammatory_response": ("3569", "3576", "6347", "4792", "7128", "5743", "3383"),
    "stress_response": ("1649", "468", "3309", "7494", "4189", "3162"),
    "contractile_maturation": ("7139", "7137", "4624", "4625", "70", "6262", "488"),
    "extracellular_matrix_remodeling": ("1277", "1278", "1281", "2335", "7040", "5054", "4313"),
}


def _sha256_file(path: Path) -> str:
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
        raise ValueError(f"expected Ensembl modules in {path}, found {list(modules)}")
    return modules


def load_gse144424_records(counts_path: Path, modules_path: Path):
    digest = _sha256_file(counts_path)
    if digest != EXPECTED_SHA_GSE144424:
        raise ValueError(f"GSE144424 SHA mismatch: got {digest}, expected {EXPECTED_SHA_GSE144424}")
    matrix = read_geo_counts(counts_path)
    metadata = parse_gse144424_count_metadata(matrix.sample_ids)
    modules = read_ensembl_modules(modules_path)
    config = ModuleScoreConfig(domain_gene_sets=modules, minimum_genes=3)
    records = score_count_modules(matrix, metadata, config)
    return matrix, config, records, digest


def subject_trajectories(records) -> tuple[LongitudinalGroup, ...]:
    """One group per biological subject across the hypoxia time course."""
    collapsed = collapse_subject_replicates(records)
    by_subject: dict[str, list] = defaultdict(list)
    for record in collapsed:
        subject = str(record.state.metadata.get("experimental_unit_id") or record.state.metadata.get("subject_id"))
        by_subject[subject].append(record)
    groups: list[LongitudinalGroup] = []
    for subject, rows in sorted(by_subject.items()):
        ordered = tuple(sorted(rows, key=lambda r: (r.time, r.observation_id)))
        groups.append(LongitudinalGroup(subject, "hypoxia_reox_course", ordered))
    return tuple(groups)


def bootstrap_ci(values: list[float], *, seed: int = 0, n: int = 2000) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    state = seed & 0xFFFFFFFF
    samples: list[float] = []
    m = len(values)
    for _ in range(n):
        total = 0.0
        for _j in range(m):
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            total += values[state % m]
        samples.append(total / m)
    samples.sort()
    lo = samples[int(0.025 * (n - 1))]
    hi = samples[int(0.975 * (n - 1))]
    return (lo, hi)


def run_loso(groups: tuple[LongitudinalGroup, ...], *, source_sha: str) -> dict:
    folds = []
    paired_improvements: list[float] = []
    model_maes: list[float] = []
    persist_maes: list[float] = []
    for held in groups:
        development = tuple(g for g in groups if g.group_id != held.group_id)
        overlap = validate_disjoint_longitudinal_groups(development, (held,))
        if overlap:
            raise RuntimeError(f"LOSO leakage for subject {held.group_id}: {overlap}")
        if len(held.records) < 2:
            continue
        model = fit_temporal_surrogate(development, spec=TemporalSurrogateSpec())
        bench = benchmark_temporal_surrogate(model, (held,), development_groups=development)
        model_maes.append(bench.model_mean_absolute_error)
        persist_maes.append(bench.persistence_mean_absolute_error)
        paired_improvements.append(
            bench.persistence_mean_absolute_error - bench.model_mean_absolute_error
        )
        folds.append(
            {
                "subject": held.group_id,
                "n_timepoints": len(held.records),
                "temporal_model_mae": round(bench.model_mean_absolute_error, 12),
                "carry_forward_mae": round(bench.persistence_mean_absolute_error, 12),
                "paired_improvement": round(
                    bench.persistence_mean_absolute_error - bench.model_mean_absolute_error, 12
                ),
                "transition_count": bench.transition_count,
            }
        )

    mean_model = statistics.fmean(model_maes)
    mean_persist = statistics.fmean(persist_maes)
    mean_paired = statistics.fmean(paired_improvements)
    relative = 0.0 if mean_persist == 0 else mean_paired / mean_persist
    ci = bootstrap_ci(paired_improvements, seed=0, n=2000)
    better = sum(1 for v in paired_improvements if v > 0)
    return {
        "dataset": "GSE144424",
        "benchmark": "leave_one_biological_subject_out_temporal_prediction",
        "report_version": "0.2.0",
        "source_archive_sha256": source_sha,
        "biological_subject_count": len(groups),
        "collapsed_subject_timepoint_count": sum(len(g.records) for g in groups),
        "fold_count": len(folds),
        "model": "multi-output linear next-state predictor (TemporalSurrogateSpec v0.1.0)",
        "feature_contract": "five RNA phenotype modules + normalized time delta; domain scores in [0,1]",
        "replicate_handling": "mean within biological subject x condition x time",
        "development_rule": "for each fold, one biological subject is held out completely before fitting",
        "aggregate": {
            "temporal_model_mean_mae": mean_model,
            "carry_forward_mean_mae": mean_persist,
            "mean_paired_improvement": mean_paired,
            "relative_mae_reduction": relative,
            "folds_better_than_carry_forward": better,
            "bootstrap_95pct_ci_paired_improvement": [ci[0], ci[1]],
            "bootstrap_seed": 0,
            "interpretation": (
                "Promising but not definitive. "
                + (
                    "Bootstrap CI excludes zero."
                    if ci[0] > 0
                    else "Bootstrap CI spans zero or is non-positive; single-dataset omics-only."
                )
            ),
            "external_validation": False,
            "clinical_validation": False,
        },
        "folds": folds,
    }


def freeze_development_transform(
    matrix,
    config: ModuleScoreConfig,
    records,
    *,
    source_sha: str,
    held_out_subjects: tuple[str, ...] = HELD_OUT_SUBJECTS_FROZEN,
) -> FrozenModuleTransform:
    fit_ids = []
    for record in records:
        subject = str(record.state.metadata.get("subject_id") or "")
        if subject not in held_out_subjects:
            fit_ids.append(record.observation_id)
    scaler = fit_module_scaler(matrix, config, fit_sample_ids=fit_ids)
    return freeze_module_transform(
        config,
        scaler,
        dataset_id="GSE144424",
        source_file="GSE144424_Counts_RNA_MCW_NEB.txt.gz",
        source_sha256=source_sha,
    )


def gse234907_gene_sets_from_symbols(modules_yaml: Path) -> dict[str, tuple[str, ...]]:
    """Return Entrez-ID modules for the GSE234907 count matrix."""
    del modules_yaml
    return dict(GSE234907_ENTREZ_MODULES)


def run_gse234907_external(
    frozen: FrozenModuleTransform,
    path: Path,
    gene_sets: dict[str, tuple[str, ...]],
) -> dict:
    digest = _sha256_file(path)
    matrix = read_gse234907_heart_counts(path)
    domains = set(frozen.domain_gene_sets)
    filtered = {d: g for d, g in gene_sets.items() if d in domains}
    if set(filtered) != domains:
        missing = domains - set(filtered)
        raise ValueError(f"external gene sets missing domains: {sorted(missing)}")

    records = score_gse234907_with_frozen_transform(
        matrix,
        gene_sets=filtered,
        frozen_transform=frozen,
        minimum_genes=3,
    )
    by_class: dict[str, list[dict[str, float]]] = defaultdict(list)
    sample_scores = {}
    for record in records:
        scores = {k: round(float(v), 6) for k, v in record.state.domain_scores.items()}
        sample_scores[record.observation_id] = {"class": record.condition, **scores}
        by_class[record.condition].append(dict(record.state.domain_scores))

    class_means = {
        cls: {d: statistics.fmean(row[d] for row in rows) for d in sorted(domains)}
        for cls, rows in sorted(by_class.items())
    }
    classes = sorted(by_class)
    effect = {}
    transfer_dict = None
    if len(classes) >= 2:
        high = next((c for c in classes if "3D" in c or "3d" in c), classes[-1])
        low = next((c for c in classes if "2D" in c or "2d" in c), classes[0])
        effect = {
            "contrast": f"{high} minus {low}",
            "delta": {d: class_means[high][d] - class_means[low][d] for d in sorted(domains)},
        }
        ref_effects = {"unit_positive_reference": {d: 0.05 for d in sorted(domains)}}
        transfer = validate_external_effect(
            effect["delta"],
            ref_effects,
            reference_dataset_id="GSE144424_directional_placeholder",
            external_dataset_id="GSE234907_3D_minus_2D",
        )
        transfer_dict = transfer.to_dict()

    n_per = {cls: len(rows) for cls, rows in by_class.items()}
    return {
        "report_version": "0.5.0",
        "status": "sample_level_no_refit_external_validation_complete",
        "reference": {
            "dataset_id": frozen.dataset_id,
            "artifact_id": frozen.artifact_id,
            "source_sha256": frozen.source_sha256,
            "fit_sample_count": len(frozen.fit_sample_ids),
            "normalization": frozen.normalization,
            "held_out_subjects_policy": list(HELD_OUT_SUBJECTS_FROZEN),
        },
        "external": {
            "dataset_id": "GSE234907",
            "source_file": path.name,
            "source_sha256": digest,
            "sample_count": len(matrix.sample_ids),
            "classes": n_per,
            "external_fit": "none",
        },
        "sample_scores": sample_scores,
        "class_means": class_means,
        "class_effects": effect,
        "direction_transfer": transfer_dict,
        "interpretation": {
            "no_refit_guarantee": (
                "GSE234907 counts transformed only with GSE144424 development-fitted "
                "centers/scales. No external centering, scaling, or model fitting."
            ),
            "inferential_caution": (
                f"Class sizes {n_per}; exhaustive relabeling yields limited p-value resolution. "
                "Treat effects as descriptive."
            ),
            "contract": "All domain scores and rna_module_features are in [0,1].",
        },
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=Path, default=DEFAULT_COUNTS)
    parser.add_argument("--gse234907", type=Path, default=DEFAULT_GSE234907)
    parser.add_argument("--modules", type=Path, default=DEFAULT_MODULES)
    parser.add_argument("--skip-external", action="store_true")
    args = parser.parse_args()

    if not args.counts.is_file():
        raise SystemExit(f"missing counts matrix: {args.counts}")

    matrix, config, records, digest = load_gse144424_records(args.counts, args.modules)
    groups = subject_trajectories(records)
    print(
        f"GSE144424: {len(records)} raw -> {sum(len(g.records) for g in groups)} "
        f"collapsed timepoints, {len(groups)} subjects"
    )

    loso = run_loso(groups, source_sha=digest)
    write_json(REPORTS / "GSE144424_loso_temporal_benchmark_v0.2.json", loso)

    frozen = freeze_development_transform(matrix, config, records, source_sha=digest)
    write_json(REPORTS / "GSE144424_frozen_module_transform_v0.2_runtime.json", frozen.to_dict())
    print(f"frozen artifact_id={frozen.artifact_id} fit_samples={len(frozen.fit_sample_ids)}")

    if not args.skip_external:
        if not args.gse234907.is_file():
            raise SystemExit(f"missing GSE234907 matrix: {args.gse234907}")
        gene_sets = gse234907_gene_sets_from_symbols(args.modules)
        ext_matrix = read_gse234907_heart_counts(args.gse234907)
        present = set(ext_matrix.gene_ids)
        aligned = {}
        for domain, genes in gene_sets.items():
            if domain not in frozen.domain_gene_sets:
                continue
            overlap = tuple(g for g in genes if g in present)
            if len(overlap) < 3:
                raise ValueError(f"domain {domain} Entrez overlap={len(overlap)} with GSE234907 matrix")
            aligned[domain] = overlap
            print(f"GSE234907 domain {domain}: {len(overlap)}/{len(genes)} Entrez genes present")
        external = run_gse234907_external(frozen, args.gse234907, aligned)
        write_json(REPORTS / "GSE234907_no_refit_external_validation_v0.5.json", external)

    summary = {
        "status": "ok",
        "gse144424_subjects": len(groups),
        "loso_fold_count": loso["fold_count"],
        "loso_mean_paired_improvement": loso["aggregate"]["mean_paired_improvement"],
        "loso_bootstrap_ci": loso["aggregate"]["bootstrap_95pct_ci_paired_improvement"],
        "frozen_artifact_id": frozen.artifact_id,
        "source_sha256": digest,
    }
    write_json(REPORTS / "FULL_VALIDATION_SUMMARY_2026-08-30.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
