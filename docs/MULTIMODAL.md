# Multimodal Cardiac State Layer

CardiVex uses one normalized state contract for downstream imaging, functional, and omics measurements. Each modality is kept separately named and then merged into a deterministic feature namespace.

## State model

```text
                 CardiacState
              /       |       \
          imaging  functional  omics
              \       |       /
               \      |      /
                domain scores
                     |
               benchmark layer
```

### Imaging

Examples of already processed features include morphology, organization, cellular architecture, and viability-derived measurements.

### Functional

Examples include normalized contractility, beat regularity, recovery kinetics, or electrophysiologic summary measurements.

### Omics

Examples include normalized pathway/signature scores or other preprocessed molecular features.

The core package intentionally consumes **processed measurements**. Raw experimental acquisition and laboratory procedures belong in separate, validated data pipelines.

## Why this matters

A realistic challenge can affect multiple biological systems simultaneously. CardiVex therefore keeps detection, novelty, and recovery evaluation multimodal instead of reducing every scenario to one generic stress score.

The first benchmark layer provides deterministic baselines:

1. Distance from healthy baseline.
2. Distance from the nearest known state.
3. Modality-specific recovery toward baseline.
4. An overall recovery score when multiple modalities are present.

These are benchmark primitives, not final ML models. More advanced representation learning can later consume the same `CardiacState` contract without changing scenario definitions.
