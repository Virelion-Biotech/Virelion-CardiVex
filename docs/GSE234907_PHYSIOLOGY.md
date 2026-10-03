# GSE234907 physiology adapter

GSE234907 is the first CardiVex functional-modality target for vascularized human cardiac organoids. The GEO Series documents simultaneous measurement of oxygen uptake, extracellular field potentials, and cardiac contraction in the underlying microphysiological system; the GEO record itself exposes the RNA-seq processed data, not the sensor traces. The adapter therefore accepts externally exported/processed sensor summaries and never reconstructs physiology from RNA-seq.

## Contract

Each observation requires:

- stable observation ID
- experimental-unit ID
- condition
- elapsed time
- processed measurement dictionary
- source reference

Each measurement must be normalized through an explicit `PhysiologicalFeatureConfig` specifying its source name, output feature name, physical lower/upper bounds, and optional inverse direction.

The resulting `IngestRecord` exposes only the modalities actually supplied. Sensor summaries become `functional`; absent imaging or omics data remain absent.

## Validation use

Keep experimental units disjoint between development and validation. Do not treat multiple time points from the same organoid as independent subjects.
