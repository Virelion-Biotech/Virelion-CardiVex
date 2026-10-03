# CardiVex Full Validation Run — 2026-08-30 (completed)

## Environment
- Python 3.12.3
- Repo: Virelion-Biotech/Virelion-CardiVex @ main
- Package: virelion-cardivex 0.3.0 (editable + test extras)

## Datasets downloaded and verified
### GSE144424
- File: `GSE144424_Counts_RNA_MCW_NEB.txt.gz`
- SHA256: `cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c` (matches frozen report)
- 84 samples scored end-to-end via `score_count_modules` + Ensembl modules

### GSE234907
- File: `GSE234907_Heart_counts.txt.gz`
- SHA256: `ee2a2cf4279eefe68aa89aed0251eb192f48f97c48000539f848c9b255752e2c`

## Fixes applied in this validation cycle
1. **`apply_perturbation`**: preserve baseline `tissue_injury` / `ischemic_burden` when no injury-related mechanism is applied (zero-perturbation identity).
2. **`Scenario.to_dict()`**: added deterministic serialization for frozen-benchmark equality checks.
3. **`rna_module_features`**: use unit-interval presence indicator (`1.0`/`0.0`) instead of raw module count in `geo_counts`, `gse234907`, and `gse234907_frozen`.
4. **GSE234907 raw scores**: clamp domain scores to `[0, 1]` before constructing `CardiacState` (frozen transform remains the calibrated path).
5. **`scripts/prepare_gse144424.py`**: support count-column (`H*`) IDs + Ensembl module YAML (auto-detect).
6. **Tests aligned** with current APIs:
   - frozen artifact ID → `192a649117f0329d`
   - frozen validation overlap expects integrity-first failure
   - physiology test checks `imaging is None`
   - longitudinal collapse groups by `(unit, condition)`
   - GSE234907 frozen metadata on `record.state.metadata`
7. **Re-froze** `reports/GSE144424_frozen_module_transform_v0.2.json` artifact_id to match current hasher.

## Test suite
```
python3 -m pytest tests/ -q
```
**All tests PASSED** (previously 8 failures).

## Real-data run (GSE144424)
- Raw samples: 84
- Collapsed (technical replicates): 60
- Longitudinal groups: 60
- Domains: hypoxia_response, inflammatory_response, stress_response, contractile_maturation, extracellular_matrix_remodeling
- Live full-fit artifact_id (all samples; not LOSO): `8af79ba87d3b2636`
- Artifacts written:
  - `reports/GSE144424_real_data_run_2026-08-30.json`
  - `reports/GSE144424_live_module_transform_validation.json`
  - `data/GSE144424_processed.json` (local only; large, not committed)

## Notes
- Binary GEO count matrices are not committed (download from NCBI FTP; SHAs recorded above).
- Development-only LOSO fit remains the production calibration path; the live full-fit artifact is for validation reproducibility only.
