# Frozen benchmark suites

A frozen benchmark suite is generated from exactly one content-hashed development calibration artifact.

The suite records the calibration artifact ID in every generated scenario's provenance. Validation requires the same artifact and uses its frozen multimodal translation profile; no calibration is refit on held-out groups.

Workflow:

```text
qualified dataset
    -> development calibration
    -> frozen calibration artifact
    -> frozen scenario generation
    -> benchmark manifest
    -> held-out validation
```

A scenario remains explicitly extrapolated until independent validation. The benchmark layer is intended to test detection, novelty/OOD behavior, attribution, temporal consistency, and recovery-oriented evaluation from downstream cardiac phenotypes without encoding pathogen construction procedures.
