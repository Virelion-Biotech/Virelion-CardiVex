# CardiVex Validation Dossier v0.3

**Date:** 2026-08-30  
**Repo:** Virelion-Biotech/Virelion-CardiVex  
**Scope:** Real-data validation of RNA module scoring, LOSO temporal prediction, and no-refit external transfer (GSE234907).

This dossier consolidates reproducible artifacts only. No metrics are claimed beyond what the linked JSON reports contain.

---

## 1. Source data integrity

| Dataset | File | SHA256 |
|---------|------|--------|
| GSE144424 | `GSE144424_Counts_RNA_MCW_NEB.txt.gz` | `cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c` |
| GSE234907 | `GSE234907_Heart_counts.txt.gz` | `ee2a2cf4279eefe68aa89aed0251eb192f48f97c48000539f848c9b255752e2c` |

Experimental unit for GSE144424 is the **biological subject** (15 subjects; 84 raw samples after technical replicates).

---

## 2. Feature contract

- Domains: hypoxia_response, inflammatory_response, stress_response, contractile_maturation, extracellular_matrix_remodeling
- Normalization: log1p(CPM) → development-only z-standardization → `0.5 + 0.15 * z`, clipped to **[0, 1]**
- `rna_module_features`: presence indicator in **[0, 1]**
- GSE144424 modules: Ensembl (`configs/gse144424_ensembl_modules.yaml`)
- GSE234907 modules: NCBI Entrez numeric IDs (`scripts/run_full_validation.py`)

---

## 3. Frozen development transform

- Runtime artifact: `reports/GSE144424_frozen_module_transform_v0.2_runtime.json`
- `artifact_id`: **27a6554942da99ba**
- Fit: 64 samples from subjects excluding held-out set `{19128, 18870, 18855}`

---

## 4. LOSO temporal benchmark (A)

**Report:** `reports/GSE144424_loso_temporal_benchmark_v0.2.json`

| Metric | Value |
|--------|------:|
| Subjects / folds | 15 |
| Collapsed subject×timepoints | 60 |
| Mean model MAE | 0.0617 |
| Mean carry-forward MAE | 0.0712 |
| Mean paired improvement | **0.00951** |
| Folds better than carry-forward | **12 / 15** |
| Bootstrap 95% CI (paired improvement) | **[-0.0056, 0.0216]** |

**Interpretation:** Temporal surrogate beats persistence on average, but bootstrap CI **includes zero**. Single-dataset, omics-only. Not clinical validation.

---

## 5. GSE234907 no-refit external validation (B)

**Report:** `reports/GSE234907_no_refit_external_validation_v0.5.json`

| Item | Value |
|------|-------|
| External fit | **none** |
| Samples | 6 (3× 1021-2D, 3× 1021-3D) |
| Largest class effect (3D−2D) | contractile_maturation ≈ **0.327** |
| Second | inflammatory_response ≈ **0.204** |

All five domain effects positive under frozen transform. n=3/class → descriptive only.

---

## 6. CI (C)

Workflow: `.github/workflows/test.yml`

1. **unit** — pytest on Python 3.10 / 3.11 / 3.12
2. **real-data-smoke** — download GSE144424, verify SHA256, run `scripts/run_full_validation.py`

If GEO download/SHA fails, smoke job skips (exit 0); unit tests remain the hard gate.

---

## 7. Reproduce locally

```bash
mkdir -p data
# place GSE144424_Counts_RNA_MCW_NEB.txt.gz (+ optional GSE234907_Heart_counts.txt.gz)
pip install -e '.[test]'
pytest
python scripts/run_full_validation.py
```

---

## 8. Known limitations

1. Omics-only; no imaging/functional modalities in these runs.
2. LOSO CI includes zero — do not overclaim temporal superiority.
3. GSE234907 n=3/class — descriptive only.
4. Entrez vs Ensembl ID spaces differ across datasets.
5. Prefer runtime JSON from the current commit over historical `artifact_id` strings.

**Bottom line:** End-to-end executable on real GEO matrices with leakage-safe LOSO and true no-refit external check. Evidence is promising and limited — platform validation, not clinical claims.
