# GSE234907 Physiology Validation

CardiVex keeps RNA and physiology as separate evidence streams until their experimental units are explicitly linked.

## Current evidence

The GSE234907 study reports integrated sensing of oxygen uptake/interstitial oxygen, extracellular field potentials, and cardiac contraction. The supplied Nature source-data workbook `41551_2023_1071_MOESM12_ESM.xlsx` has SHA-256 `cdb2b8779647c53ff2e8506eca896d8c11c06bcb4ad0b353eb4cf9aebe306763`.

The relevant workbook sheet `ED Fig 2` explicitly contains the GEO RNA sample IDs `S10_2`, `S11_2`, and `S12_2`, all labeled `1021-3D`, with physiology-related OCR/basal-respiration fields.

The workbook does not contain the 2D RNA IDs `S7_2`, `S8_2`, or `S9_2`. CardiVex therefore records **partial linkage**, not complete six-sample pairing.

## Linkage rule

Do not infer sample pairing from:

- 2D/3D labels alone
- sample ordering
- filenames
- presumed biological replicate order

Sample-level RNA-to-physiology analysis requires an explicit one-to-one mapping with a provenance reference.

An exploratory paired analysis may use the explicitly linked S10_2/S11_2/S12_2 subset as n=3 descriptive evidence, but complete six-sample validation remains blocked.

## API

Use `audit_physiology_linkage()` and `require_sample_level_ready()` from `cardivex.physiology_linkage` before any complete sample-level RNA-to-physiology correlation or prediction.
