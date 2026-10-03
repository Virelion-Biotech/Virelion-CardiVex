# Frozen-calibration scenario generation

CardiVex can generate a computational downstream-phenotype scenario directly from a frozen development calibration artifact.

## Contract

1. Verify the artifact digest before generation.
2. Select exactly one calibrated condition.
3. Reuse its empirical phenotype profile, correlation structure, and empirical temporal profile.
4. Do not fit or refit anything during scenario construction.
5. Record the calibration artifact ID in scenario provenance and variation metadata.
6. Keep generated states explicitly extrapolated until independent validation is available.

This layer operates on measured phenotype representations and does not encode procedures for creating or modifying biological agents.
