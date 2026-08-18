# GSE234907 Physiology Validation

CardiVex keeps RNA and physiology as separate evidence streams until their experimental units are explicitly linked.

## Current evidence

The GSE234907 study reports integrated sensing of oxygen uptake/interstitial oxygen, extracellular field potentials, and cardiac contraction. Its public source data are provided with the paper.

The six GEO RNA samples in the current benchmark are `S7_2`, `S8_2`, `S9_2`, `S10_2`, `S11_2`, and `S12_2`, grouped as 2D and 3D.

## Linkage rule

Do not infer sample pairing from:

- 2D/3D labels alone
- sample ordering
- filenames
- presumed biological replicate order

Sample-level RNA-to-physiology analysis requires an explicit one-to-one mapping with a provenance reference.

Without that mapping, CardiVex permits only descriptive group-level comparisons.

## API

Use `audit_physiology_linkage()` and `require_sample_level_ready()` from `cardivex.physiology_linkage` before any sample-level RNA-to-physiology correlation or prediction.
