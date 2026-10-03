# Dataset analysis plans

`build_analysis_plan()` converts a qualified processed dataset into an explicit downstream plan.

It records which observations are available for empirical profiling, which experimental units can support longitudinal validation, which observations contain all three supported modalities, and which groups are candidates for a held-out evaluation split.

The plan is descriptive and deterministic. It does not infer causality or promote a dataset to biological validation merely because it passes software checks.

Recommended workflow:

1. ingest processed observations;
2. qualify the dataset;
3. build the analysis plan;
4. freeze development/held-out groups before calibration;
5. fit empirical profiles and translation mappings only on development data;
6. validate on disjoint held-out units;
7. retain the plan and hashes as part of the audit artifact.
