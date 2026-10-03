# Calibration and uncertainty

CardiVex distinguishes three quantities that are often conflated:

1. **Scenario support** — how strongly a generated state is grounded in source observations.
2. **Scenario calibration error** — how close a generated phenotype vector is to a held-out measured vector.
3. **Uncertainty** — how variable the underlying observations are.

## Workflow

```text
observed records
      |
      +--> empirical distribution + uncertainty band
      |
      +--> scenario generation
      |
      +--> held-out observation comparison
                   |
                   v
             calibration error
```

A low calibration error is evidence that a computational state resembles the selected validation observations. It does not establish causal realism or predict a real event.

## Uncertainty handling

Domain-level uncertainty is summarized with a mean and a simple normal-approximation interval. This is a transparent baseline for benchmarking and should be replaced with appropriate inferential procedures when the underlying study design warrants them.

## Benchmark rule

Thresholds, calibration profiles, and uncertainty estimates must be fitted only from permitted development data. Held-out challenge states and final test observations must not influence these settings.
