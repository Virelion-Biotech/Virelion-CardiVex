# Dataset qualification

CardiVex distinguishes a dataset being available from a dataset being suitable for a particular scientific task.

`qualify_records()` checks dataset identity, modality coverage, experimental-unit metadata, expected longitudinal coverage, and required modality availability.

Recommended uses are conservative:

- `domain_profile`: available when processed domain measurements exist.
- `longitudinal_surrogate_validation`: requires complete expected time coverage and at least two experimental units.
- `multimodal_calibration`: requires observed imaging, functional, and omics measurements.

Qualification is a gate, not biological validation. A qualified dataset can still be unsuitable for a particular question because of sample size, model system, batch effects, or external generalizability.
