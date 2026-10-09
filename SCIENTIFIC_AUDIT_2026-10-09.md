# Scientific audit changes — 2026-10-09

## Behavior

Add novelty-positive rank AUROC and tie-aware average precision, recording evaluation prevalence and leaving independent-unit count unknown.

## Scope and remaining evidence

Average precision is the noninterpolated PR summary, not an estimated deployment-prevalence metric. No new external cohort or additional detector is qualified. Threshold selection must remain independent of scored test data.

## Implementation

- `tests/test_ood_ranking.py`
- `cardivex/evaluation.py`

## Verification

Regression tests accompany the changes. Repository test results are recorded in the audit completion report and draft pull request. Software regression checks do not establish numerical, biological, transport or clinical validity.
