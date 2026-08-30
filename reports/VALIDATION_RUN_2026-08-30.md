# CardiVex Full Validation Run — 2026-08-30

## Environment
- Python 3.12.3
- Repo: Virelion-Biotech/Virelion-CardiVex @ main (cloned 2026-08-30)
- Package: virelion-cardivex 0.3.0 installed editable with [test]

## Datasets Downloaded
### GSE144424
- File: GSE144424_Counts_RNA_MCW_NEB.txt.gz
- Source: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE144nnn/GSE144424/suppl/GSE144424_Counts_RNA_MCW_NEB.txt.gz
- Size: 2,660,472 bytes
- SHA256: cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c
- **Matches** the SHA committed in reports/GSE144424_frozen_module_transform_v0.2.json

### GSE234907
- File: GSE234907_Heart_counts.txt.gz
- Source: https://ftp.ncbi.nlm.nih.gov/geo/series/GSE234nnn/GSE234907/suppl/GSE234907_Heart_counts.txt.gz
- Size: 275,444 bytes
- SHA256: ee2a2cf4279eefe68aa89aed0251eb192f48f97c48000539f848c9b255752e2c

## Test Suite Results
Ran: `python3 -m pytest tests/ -q`

- Total tests discovered: ~52
- **8 FAILED**
- Remaining PASSED

### Failures
1. tests/test_cardiac_state.py::test_zero_perturbation_preserves_baseline_state
   - tissue_injury: 0.0 != 0.02 (state equality after zero perturbation)
2. tests/test_frozen_benchmark.py::test_frozen_benchmark_is_deterministic
   - AttributeError: 'Scenario' object has no attribute 'to_dict'
3. tests/test_frozen_validation.py::test_frozen_validation_rejects_artifact_record_overlap
   - ValueError: calibration artifact integrity check failed (expected regex mismatch)
4. tests/test_gse144424_frozen_artifact.py::test_corrected_gse144424_frozen_parameters_are_complete_and_stable
   - AssertionError: artifact_id '192a649117f0329d' != expected '27a6554942da99ba'
5. tests/test_gse234907.py::test_score_gse234907_modules_remains_omics_only
   - ValueError: domain 'module' must be in [0, 1]
6. tests/test_gse234907_frozen.py::test_gse234907_frozen_scorer_does_not_fit_external_data
   - ValueError: feature 'rna_module_features' must be in [0, 1]
7. tests/test_physiology.py::test_ingest_preserves_experimental_unit_and_functional_only
   - AttributeError: 'NoneType' object has no attribute 'values'
8. tests/test_real_gse144424.py::test_collapse_subject_replicates
   - AssertionError: assert 2 == 1 (group count after collapse)

## Observations
- Primary count matrix for GSE144424 downloads cleanly and SHA matches frozen reports.
- Raw module scores (log1p CPM mean) fall outside the [0, 1] contract enforced by `features.py` / `ModalityVector`; the frozen transform (development-only z + 0.15 scale around 0.5) is required for valid CardiacState construction.
- Several unit tests appear out of sync with current class APIs (missing `to_dict`, changed artifact hashing, changed default tissue_injury, replicate collapse logic).
- `scripts/prepare_gse144424.py` expects the GSM-keyed sample_map + symbol gene lists; the committed counts file uses H* column names + Ensembl IDs. Use `parse_gse144424_count_column` + ensembl modules instead.
- No end-to-end `run_benchmark_suite` execution was performed against freshly scored real data because of the range-validation barrier and test failures.

## Recommendation
1. Recompute / freeze the GSE144424 module transform artifact so the committed artifact_id matches the current hashing implementation.
2. Align Scenario serialization, CardiacLatent defaults, and replicate-collapse tests with the current code.
3. Update prepare script (or add a counts-column path) for the Ensembl matrix.
4. Re-run full suite + regenerate reports/ after fixes.
5. Consider relaxing or documenting the hard [0,1] clamp for intermediate module scores vs final CardiacState features.

## Artifacts produced by this run
- data/GSE144424_Counts_RNA_MCW_NEB.txt.gz (downloaded, not committed — large binary)
- data/GSE234907_Heart_counts.txt.gz (downloaded, not committed)
- reports/VALIDATION_RUN_2026-08-30.md (this file)
