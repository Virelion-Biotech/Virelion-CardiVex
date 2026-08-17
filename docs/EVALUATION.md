# CardiVex Evaluation Layer

CardiVex now includes transparent evaluation primitives before any learned model is introduced.

## Threshold calibration

`calibration_curve()` evaluates candidate abnormality thresholds against labeled benchmark scores and returns sensitivity, specificity, and balanced accuracy. `best_threshold()` selects the highest-balanced-accuracy operating point with deterministic tie-breaking.

Thresholds should be calibrated on a dedicated calibration split and frozen before reporting test performance.

## OOD evaluation

`ood_evaluate()` evaluates the nearest-known-state distance as a simple out-of-distribution baseline. It reports:

- true-positive rate on held-out novel states
- false-positive rate on known states
- counts of known and novel samples

This is intentionally interpretable and should remain in benchmark reports even after learned OOD models are added.

## Evaluation discipline

Recommended split structure:

```text
train
  -> model fitting
calibration
  -> threshold selection / calibration
validation
  -> model selection
held_out_novel
  -> novelty benchmark
final test
  -> one-time performance estimate
```

Exact scenario definitions, transformed feature vectors, and direct copies of held-out measurements must not cross split boundaries.

## What this layer does not claim

These metrics evaluate the computational benchmark. They do not establish that a scenario is a real event, that a phenotype mapping is biologically validated, or that a recovery score demonstrates therapeutic efficacy. Those claims require independent evidence.
