# Modeling and Benchmark Strategy

CardiVex uses transparent baselines before introducing complex machine-learning models.

## Current baseline

`cardivex.modeling.CentroidModel` fits one centroid per label and classifies a processed cardiac state by nearest normalized distance. It has no external ML dependency and is intentionally interpretable.

The baseline establishes:

- a reproducible reference point for future models;
- a feature-contract compatibility test;
- a simple confidence proxy (`1 - distance`);
- a deterministic prediction path suitable for audit records.

It is not intended to represent the final defensive model.

## Split discipline

Every scenario belongs to exactly one of:

```text
train
validation
 test
held_out_novel
```

`BenchmarkSplit.validate()` enforces unique scenario IDs and checks the held-out group for direct leakage against the combined development/evaluation groups.

Thresholds and model-selection decisions should be made using training/development data only. The held-out novel group is reserved for final novelty assessment.

## Next model stages

The architecture is ready for progressively stronger models while preserving the same state contract:

1. linear/logistic baseline;
2. tree-based baseline;
3. calibrated multimodal fusion;
4. temporal models;
5. representation-learning and OOD models.

Every new model should report the transparent centroid and distance-based baselines alongside its own results.

## Interpretation boundary

Model performance on synthetic challenge states demonstrates computational performance on those representations. It does not establish performance against an unmeasured real-world event. Evidence quality, proxy validity, and scenario realism remain separate evaluation dimensions.
