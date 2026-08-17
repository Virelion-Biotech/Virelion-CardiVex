# Development Calibration Runner

`build_development_calibration` freezes empirical calibration state from one qualified dataset while excluding the analysis plan's candidate held-out longitudinal groups before fitting any component.

The artifact can contain, per condition:

- empirical phenotype distributions;
- empirical domain correlations;
- an empirical temporal profile when multiple time points exist;
- a matched imaging/function/omics translation profile when enough complete observations exist.

The artifact records development observation IDs, excluded held-out observation IDs, held-out group IDs, source dataset IDs, and a deterministic artifact ID.

## Leakage rule

Held-out candidate groups are excluded before phenotype, correlation, temporal, or multimodal calibration is fit. The artifact should therefore be treated as the frozen development state for the subsequent surrogate-validation stage.

This is a descriptive calibration layer. It does not infer initiating procedures or causal mechanisms and does not establish that a generated scenario is biologically validated.
