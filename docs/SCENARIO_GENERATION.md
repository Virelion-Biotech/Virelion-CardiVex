# Scenario Generation

CardiVex constructs computational challenge states from downstream cardiac phenotype observations rather than from instructions for generating an initiating biological agent.

## Generation ladder

```text
processed observations
        ↓
empirical phenotype profile
        ↓
bounded scenario sampling
        ↓
temporal trajectory
        ↓
novelty assessment
        ↓
held-out benchmark state
```

## Empirical profiles

`fit_empirical_profile()` summarizes domain distributions by condition. The profile retains:

- domain mean
- standard deviation
- observed range
- sample count
- source dataset identifiers

The profile is the bridge between measured data and scenario construction.

## Bounded generation

`build_challenge_scenario()` samples around empirical domain centers using bounded deviations and a deterministic seed. The result records its parent datasets and transformation history.

A scenario is marked `validated_model` only when there is enough empirical support; small synthetic fixtures remain explicitly exploratory.

## Temporal trajectories

`bounded_trajectory()` provides a simple abstract onset → peak → recovery trajectory. `shift_timeline()` permits bounded timing changes without changing phenotype magnitude.

Temporal shifts should be treated as novel benchmark conditions unless supported by independent observations.

## Novelty

Novelty is evaluated against a reference collection using normalized phenotype distance. A held-out scenario is useful only if the candidate itself and any transformed copy of its measurements remain excluded from training.

## Limitations

These generators are benchmark primitives. Their output should not be interpreted as a prediction of an actual future event unless independently calibrated against relevant observations. More advanced empirical distributions, covariance-aware sampling, uncertainty propagation, and learned generative representations can replace these primitives later while keeping the scenario contract unchanged.
