# Evidence and Dataset Registry

CardiVex separates **scenario definitions** from the evidence that supports them. This prevents a synthetic challenge from silently becoming its own source of truth.

## Evidence records

An `EvidenceRecord` identifies where a host-response observation came from and records the modality, population, timepoint, and a quality score. The registry is deterministic and rejects duplicate evidence identifiers.

## Dataset records

A `DatasetRecord` is the metadata contract for an input dataset. It records:

- dataset identity and version
- species and model
- assay types
- condition labels
- source reference
- processed feature contract
- linked evidence identifiers

The registry deliberately stores **metadata and provenance**, not laboratory procedures.

## Recommended ingestion flow

```text
external dataset
      ↓
metadata extraction
      ↓
DatasetRecord
      ↓
quality / provenance review
      ↓
processed feature extraction
      ↓
CardiacState
      ↓
scenario calibration / validation
```

A dataset should not be promoted to evidence for a scenario merely because it exists. The feature mapping, population/model compatibility, temporal alignment, and assay quality should be reviewed first.

## Why this matters for realistic challenges

The challenge engine can later use evidence-linked distributions rather than hand-picked point values. That lets the project distinguish:

`measured response` → `validated surrogate` → `bounded variation` → `hypothetical novel state`

and report the supporting evidence separately from the model-derived components.
