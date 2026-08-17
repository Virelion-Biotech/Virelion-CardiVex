# Temporal realism

CardiVex supports two trajectory modes.

## Empirical mode

Processed observations are grouped by condition and time. For each time point, the system computes a descriptive mean and uncertainty for each downstream phenotype domain. Time can be normalized to a `[0, 1]` trajectory while preserving the original dataset provenance.

An `EmpiricalTemporalProfile` can then be materialized into a generated scenario with explicit severity and time scaling. The generated state remains extrapolated until independent validation is available.

## Fallback mode

When no temporal data are available, the builder retains the simple abstract trajectory used by early prototypes. This mode is explicitly recorded as `abstract_temporal_fallback` in provenance and should not be treated as experimentally calibrated temporal behavior.

## Benchmark rule

Temporal-shift challenges should modify the timing of an empirically grounded trajectory, not invent a new trajectory without evidence. A scenario report should therefore distinguish:

- observed temporal profile
- empirical profile-derived scenario
- temporal-shifted extrapolation
- abstract fallback

This separation prevents a mathematically convenient trajectory from being mistaken for a validated biological response.
