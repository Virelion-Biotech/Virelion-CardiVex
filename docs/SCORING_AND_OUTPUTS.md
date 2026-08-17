# Scoring and Outputs

CardiVex separates scenario construction from evaluation. The scoring layer converts one end-to-end assessment into interpretable overall, modality-specific, novelty, and attribution metrics.

## Modality scoring

Imaging, functional, and omics vectors are evaluated independently when available. Missing modalities are reported as unavailable rather than synthesized.

## Attribution coverage

Domain attribution is a ranked diagnostic decomposition of deviation from baseline. It is not causal inference. The coverage score records how much of the observed deviation is represented by the reported domain contributions.

## Recovery

Recovery is calculated against the same baseline used for the challenge assessment. Modality-level recovery is retained alongside the aggregate score.

## Serialization

`cardivex.serialization.dumps()` converts dataclasses, mappings, tuples, and enum-like values into deterministic JSON-safe objects. `write_json()` provides a stable file output for benchmark artifacts.

The output contract is intentionally plain JSON so later dashboards, notebooks, and external reporting systems can consume the same benchmark results without depending on Python internals.
