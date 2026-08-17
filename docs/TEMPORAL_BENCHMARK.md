# Temporal benchmark discipline

The temporal surrogate is evaluated against a persistence baseline before its predictive value is interpreted.

## Reference baseline

Persistence predicts the next state as the current state for every modeled domain. It is intentionally non-parametric and requires no fitting data.

## Reported quantities

- `model_mean_absolute_error`: held-out domain-level MAE from the temporal surrogate.
- `persistence_mean_absolute_error`: held-out MAE from the persistence baseline.
- `improvement_vs_persistence`: relative reduction in MAE, calculated as `(persistence - model) / persistence`.
- `transition_count`: number of evaluated consecutive transitions.
- `evaluated_domain_values`: number of domain-level prediction errors contributing to MAE.

A positive improvement means the temporal model outperformed persistence on the held-out data. A negative value means persistence was better.

## Leakage rule

Development and held-out experimental-unit IDs must be disjoint. The benchmark checks this before evaluating any transition. The model is never refit during benchmarking.

## Interpretation

This benchmark tests whether the longitudinal representation contains predictive signal beyond simply carrying the current state forward. It is not evidence that the surrogate is a validated physiological simulator. Results should be reported together with the held-out transition count and domain coverage.
