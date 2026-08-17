# Surrogate validation runner

`run_surrogate_validation` is the reproducible entry point for evaluating development-derived challenge representations on disjoint longitudinal experimental units.

The runner requires non-overlapping development and held-out group IDs. It evaluates each supplied scenario against each held-out group and returns deterministic ordering plus a run identifier derived from the scenario and group IDs.

The result reports domain trajectory error, temporal similarity, modality-specific validation, aggregate multimodal error, source dataset IDs, and split cleanliness.

This is a validation harness, not evidence that the underlying surrogate is biologically validated. Scientific claims require independently curated measured observations and a predeclared acceptance protocol.
