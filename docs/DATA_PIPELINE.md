# CardiVex Data Pipeline

CardiVex now has an explicit path from reviewed dataset metadata to benchmark-ready cardiac states.

```text
DatasetRegistry
      |
      v
processed CSV / row records
      |
      v
loader.py
      |
      v
IngestRecord
      |
      v
quality checks
      |
      v
DatasetBatch
      |
      +----------------+
      |                |
  by-condition    by-timepoint
      |                |
      +--------+-------+
               v
        CardiacState
               |
               v
   scenario / modeling / benchmark
```

## Input contract

The generic CSV loader expects:

- `observation_id`
- `dataset_id`
- `condition`
- `time`

Optional columns may contain JSON objects for `domain_scores`, `imaging`, `functional`, and `omics`, plus `source_ref`.

The loader consumes **already processed measurements**. It does not implement raw image processing, sequencing alignment, laboratory acquisition, or experimental procedures.

## Quality gates

Every ingestion batch can be inspected for:

- duplicate observation IDs
- missing source references
- observations with no modalities
- observations with no domain scores

Errors should block benchmark use. Warnings remain visible for provenance review.

## Condition handling

`DatasetBatch` provides deterministic condition filtering. This is deliberately simple so benchmark construction can remain explicit; train/test assignments should be created using the existing split machinery rather than inferred implicitly from condition names.

## Missing modalities

Missing modalities remain missing. CardiVex does not silently impute them at ingestion. A downstream benchmark can call `require_modalities()` when a specific analysis requires a defined modality set.

## Next data-development stage

Future dataset-specific adapters can map curated imaging, functional, or omics tables into the same `ingest_processed_observation()` interface. This keeps dataset-specific parsing separate from the model and benchmark contracts.
