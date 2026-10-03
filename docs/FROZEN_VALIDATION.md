# Frozen Development Calibration Validation

CardiVex separates calibration from held-out validation.

1. A dataset is qualified and an analysis plan identifies candidate held-out experimental units.
2. `build_development_calibration` removes those groups before fitting phenotype distributions, correlations, temporal profiles, or multimodal translation.
3. The resulting `CalibrationArtifact` is content-hashed with `compute_artifact_id`.
4. `run_frozen_validation` verifies that digest and that the supplied held-out groups exactly match the artifact declaration.
5. Validation consumes the frozen translation profile only; it does not refit calibration on held-out observations.

The artifact is therefore a reproducibility boundary. It is not a claim that the resulting surrogate is biologically valid; that conclusion requires independent measured validation and a predeclared acceptance protocol.
