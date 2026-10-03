# Temporal predictive surrogate

CardiVex includes a transparent multi-output linear next-state baseline for longitudinal cardiac-state prediction.

## Contract

The model is fit only from consecutive transitions within development experimental units. Held-out units are evaluated without refitting. Overlapping experimental-unit IDs are rejected before evaluation.

For a current domain vector `x_t` and elapsed time `Δt`, the model predicts the next domain vector `x_(t+1)` using standardized current-domain features and optional time delta. Outputs are clipped to the normalized `[0, 1]` downstream state range.

## Why this baseline exists

It is intentionally simple. It establishes whether the empirical longitudinal representation contains predictive signal before introducing more complex temporal models. It should not be described as a validated physiological simulator.

## Evaluation

The held-out report includes mean absolute error, maximum absolute error, transition count, and evaluated domain-value count. Training fit statistics are not substituted for held-out performance.
