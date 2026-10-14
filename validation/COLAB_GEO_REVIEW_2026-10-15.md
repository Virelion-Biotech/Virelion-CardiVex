# GEO Colab results and classification scope correction

`05_CardiVex_GEO_v1_results.zip` completed all three runners in 61.10 seconds
with return code zero. All 29 unique members are retained under
[`colab_geo_2026_10_15/original`](colab_geo_2026_10_15/original/), including
supplied launchers as inert `.py.txt` files. All 28 original manifest hashes
match, as do launcher hashes and the canonical protocol identity. The 237-file
source snapshot matches pinned commit `dccfdb4b3f34223d59f5ccd822e4f975c3dc2cd5`;
the base checkout's 80 implementation/configuration files also match the run.
The supplied launchers were not executed in this review.

The review independently downloaded all three pinned GEO count archives and
verified their SHA-256 hashes. All three repository runners were rerun on CPU.
Every original field in all seven result reports was reproduced; additional
reporting fields and caution text do not replace the original export. Original
evidence and new reports are kept in separate directories. `REVIEW.json` records
the checks and `PAYLOAD_SHA256.json` covers the retained and derived artifacts.

## Correctable scientific reporting issue

The delta classifier subtracts a subject's known normoxia measurement from each
condition. This is valid for a paired experimental task if that reference is
available at inference. However, the normoxia measurement itself becomes exactly
zero. Scoring the supplied reference as an unknown query can make the aggregate
accuracy look stronger than performance on the remaining samples.

The classifier, five curated RNA modules, donor splits, fold-fitted scaling, and
parameters are unchanged. Each LOSO runner now reports `query_only` metrics,
excluding normoxia by original acquisition condition, and the classification
runner exports subject/condition/prediction rows. Exclusion uses the original
condition even when normoxia is mapped to the binary label `other`. Known
references remain available for delta computation and model training. Existing
baseline-inclusive fields are retained and explicitly labeled for compatibility.

| Evaluation | Baseline-inclusive original score | Non-reference query score |
|---|---:|---:|
| Absolute four-class classifier | 27/60 = 45.0% | 21/45 = 46.7% |
| Delta four-class classifier | 39/60 = 65.0% | 24/45 = 53.3% |
| Delta hypoxia versus other | 54/60 = 90.0% | 39/45 = 86.7% |

Both query evaluations retain the original classifier's prediction space.
Thus a query predicted as normoxia still counts as an error in the four-class
task. Query-only four-class macro F1 is 0.46777 under the union of observed and
predicted labels; binary query macro F1 is 0.85453. There are 45 repeated
subject/condition queries but only 15 biological subjects, not 45 independent
donors. The hypoxia-versus-normoxia task has only hypoxia left after excluding its
reference: its query accuracy is recall, not a binary discrimination score.

This corrects reporting scope; it does not improve the fitted classifier or
establish clinical diagnostic accuracy. Poor reoxygenation separation remains.
Selecting new genes, models or thresholds on these repeatedly inspected donors
would be exploratory development and needs a separate locked cohort before a
generalization claim.

## Frozen-suite sample accounting

The frozen suite compares five scenarios against the same three held-out
subjects. Its 15 comparison rows are not 15 independent biological validations.
The runner now exports `held_out_subject_count=3`,
`validation_comparison_count=15`, and the sampling-unit explanation. The original
calibration artifact and scenario outputs remain unchanged. Content hashes and
split isolation establish reproducibility, not realism of novel challenges.

## Limits left unresolved

- Temporal MAE is 0.061354 versus persistence 0.070862, a 13.4% point reduction.
  The subject-paired mean improvement is 0.009508 with bootstrap interval
  [-0.005733, 0.021684]. This run cannot establish temporal superiority.
- GSE234907 contains six samples, three per design class, and uses a different
  2D/3D contrast. No-refit expression transformations are descriptive cross-study
  checks, not an independent hypoxia benchmark. All five exact two-sided tests
  give p=0.1. Donor/batch independence and cross-platform biological comparability
  need separate review before stronger inference.
- The 56 RNA/ATAC pairs establish subject/condition alignment. The ATAC quantity
  is library-depth QC, with no peak-to-gene biological accessibility scoring;
  its correlations are not functional multimodal validation.
- Independent novelty/OOD truth, calibrated uncertainty coverage, functional
  recovery measurements and larger matched external cohorts are absent from
  this run. These gaps cannot be repaired by changing the reported point scores.

## Verification and reproduction

192 local tests passed with 90.15% package statement coverage. Regression tests
cover exclusion by condition rather than binary label, empty query sets, LOSO
prediction rows, and repeated-scenario subject accounting. Fresh empirical
contract verification also passed.

```bash
python -m pip install -e '.[test,reference]'
python scripts/download_validation_data.py
python scripts/run_full_validation.py --output-dir /tmp/cardivex-review
python scripts/run_improved_classification.py --output-dir /tmp/cardivex-review
python scripts/run_next_validation_bundle.py --output-dir /tmp/cardivex-review
python scripts/verify_real_validation.py /tmp/cardivex-review
```

No notebook execution repair is required. The existing pinned notebook remains
an accurate record of its original code; new runner executions export the
additional query-scope and sampling-unit fields.
