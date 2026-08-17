# Virelion-CardiVex

CardiVex is a computational challenge and evaluation platform for human cardiac models. It represents realistic, non-operational biological challenge states and evaluates whether analysis systems can detect abnormality, characterize affected biological systems, recognize unfamiliar states, quantify recovery, and reproduce every conclusion.

## Core question

> Can a human cardiac digital surrogate and defensive analysis system remain effective when a challenge produces an unusual or previously unseen phenotype?

## Platform

```text
Scenario evidence
      |
      v
Scenario registry
      |
      v
Scenario translation
      |
      v
Cardiac digital surrogate
      |
      +-------------------+
      |                   |
 observed/proxy     bounded synthetic
      |                   |
      +---------+---------+
                |
                v
       multimodal state
                |
      +---------+----------+
      |                    |
      v                    v
 detection            novelty / OOD
      |                    |
      +---------+----------+
                |
                v
       mechanism attribution
                |
                v
        countermeasure test
                |
                v
          rescue scoring
                |
                v
        audit + provenance
```

## Repository layout

- `cardivex/` — scenario, translation, multimodal state, defense, attribution, realism, benchmark, evaluation, pipeline, and audit logic.
- `schemas/` — machine-readable scenario and cardiac-state definitions.
- `examples/` — scenario and evaluation fixtures.
- `docs/` — architecture, scenario specification, multimodal design, and evaluation methodology.
- `tests/` — deterministic unit tests for the benchmark layer.

## Current implementation

- Typed scenario objects with evidence tiers and uncertainty.
- Bounded phenotype-level scenario variation with deterministic seeds.
- Temporal interpolation of abstract cardiac response states.
- A normalized `CardiacState` contract spanning imaging, functional, and omics features.
- Modality adapters for already-processed measurements.
- Transparent scenario-to-multimodal translation profiles.
- End-to-end detection and domain-attribution pipeline.
- Baseline abnormality scoring.
- Nearest-known-state distance as an interpretable OOD baseline.
- Threshold calibration with sensitivity, specificity, and balanced accuracy.
- Held-out OOD evaluation with true-positive and false-positive rates.
- Multimodal recovery scoring with modality-specific and overall rescue estimates.
- Realism scoring that penalizes uncertainty and extrapolation.
- Hash-based audit records for reproducibility.
- Benchmark leakage checks for held-out scenarios.
- Automated tests and a Python 3.10–3.12 GitHub Actions matrix.

## Evaluation discipline

The recommended benchmark flow is:

```text
train
  -> model fitting
calibration
  -> threshold selection
validation
  -> model selection
held-out novel
  -> OOD/generalization benchmark
final test
  -> one-time performance estimate
```

Thresholds selected during calibration should be frozen before final test evaluation. Exact held-out scenario definitions and transformed feature representations must remain isolated from training.

See [`docs/EVALUATION.md`](docs/EVALUATION.md) for the evaluation methodology.

## Multimodal state layer

```text
              CardiacState
            /      |       \
       imaging  functional   omics
            \      |       /
             \     |      /
              domain scores
                   |
             benchmark layer
```

See [`docs/MULTIMODAL.md`](docs/MULTIMODAL.md) for the state contract and adapter philosophy.

## Scenario philosophy

CardiVex separates **scenario realism** from **scenario certainty**. A scenario can be deliberately unfamiliar while still being grounded in measured host-response evidence. Every scenario records where its features came from and which transformations were applied.

The challenge engine works at the level of measurable host-response phenotypes and temporal behavior. It does not encode procedural instructions for creating, modifying, optimizing, or deploying a biological agent.

## Validation ladder

```text
observed reference
       -> characterized proxy
       -> validated computational representation
       -> bounded synthetic variation
       -> held-out novel scenario
```

Claims become more exploratory as a scenario moves rightward. Held-out scenarios are kept separate from training inputs to prevent leakage.

## Development

```bash
pip install -e '.[test]'
pytest
```

The project is intentionally modular so future imaging, functional, transcriptomic, and ML implementations can consume the same scenario, cardiac-state, benchmark, evaluation, pipeline, and audit contracts instead of inventing incompatible representations.
