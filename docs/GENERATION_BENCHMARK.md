# Generation Benchmark Protocol

The scenario generator is evaluated as a modeling component, not as a source of biological-agent construction instructions.

## Required benchmark families

1. **Reconstruction** — generated states should remain close to their source empirical profile within declared uncertainty.
2. **Bounded variation** — repeated seeds should produce deterministic outputs and never exceed configured domain bounds.
3. **Temporal shift** — timing perturbations should preserve phenotype magnitudes while changing only the declared temporal parameters.
4. **Combinatorial novelty** — mixtures of known downstream phenotype profiles should be compared with known reference states and explicitly labeled as novel when sufficiently distant.
5. **Leakage resistance** — generated held-out states and transformed copies must never enter training collections.
6. **Pipeline consistency** — every generated state must pass through the same `CardiacState`, assessment, and audit contracts used by measured observations.

## Empirical calibration

The minimum useful real-data inputs are repeated processed observations with:

- stable observation identifiers
- dataset identifiers
- condition labels
- timepoints
- normalized phenotype domains
- provenance references

`fit_empirical_profile()` estimates domain distributions. `domain_correlation_matrix()` estimates pairwise relationships that can later be used by more advanced samplers.

## Novel-state rule

Novelty is about the observed downstream phenotype representation. A state is not considered novel merely because it has a new identifier or narrative description. It must be quantitatively different from the reference distribution under the selected benchmark metric.

## Interpretation

A high generation score means the synthetic state is internally consistent with the selected empirical representation. It does not establish that an initiating cause is realistic. External validation is required before using generated states to support scientific conclusions.
