# Processed Observation Ingestion

CardiVex ingests **processed observations** into the shared `CardiacState` contract. The ingestion boundary is deliberately separate from raw experimental acquisition and raw-data processing.

## Flow

```text
dataset registry
      |
      v
reviewed observation metadata
      |
      v
processed imaging / functional / omics features
      |
      v
cardivex.ingest
      |
      v
CardiacState + provenance
```

## Invariants

Every observation must have:

- a stable observation identifier;
- a dataset identifier;
- a condition label;
- a non-negative time coordinate;
- normalized domain scores;
- explicit indication of which modalities are present.

Missing modalities are not silently imputed by the ingestion layer. Benchmarks that require a modality must call `require_modalities()` and fail explicitly when it is absent.

## Provenance

The resulting `CardiacState.metadata` carries the observation ID, dataset ID, condition, and source reference. This keeps downstream benchmark outputs traceable to their originating observation metadata.

## Boundaries

The package accepts processed numerical measurements only. It does not implement raw experimental acquisition or laboratory procedures. A separate validated data-processing pipeline can transform approved source data into the ingestion contract.
