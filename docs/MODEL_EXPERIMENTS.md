# Model experiments

CardiVex keeps model development separate from scenario construction. Models consume processed feature representations and are evaluated against declared benchmark splits.

## Baseline workflow

```text
processed CardiacState features
        |
        v
training split
        |
        v
transparent centroid model
        |
        +--> class-aware cross-validation
        |       +--> accuracy
        |       +--> balanced accuracy
        |       +--> macro F1
        |
        +--> calibration split
        |
        +--> held-out novel split
```

Cross-validation is deterministic and assigns observations within each class in round-robin order. A fold is rejected when its training partition loses a class entirely.

## Model lineage

Each benchmarked model should be registered with:

- model ID and version
- feature contract
- training split
- notes describing intended use

This metadata complements the benchmark audit record and prevents an evaluation result from becoming detached from the model that produced it.

## Interpretation

The centroid model is intentionally transparent. It is a benchmark reference, not the intended final architecture. More complex models should be compared using the same feature contract and split definitions.

Balanced accuracy and macro F1 are reported alongside ordinary accuracy so class imbalance cannot be hidden by a single aggregate score.
