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

- `cardivex/` — scenario, translation, multimodal state, defense, attribution, realism, benchmark, pipeline, and audit logic.
- `schemas/` — machine-readable scenario and cardiac-state definitions.
- `examples/` — example scenario objects.
- `docs/` — architecture, scenario specification, validation rules, and multimodal design.
- `tests/` — deterministic unit tests for the core benchmark layer.

## Current implementation

- Typed scenario objects with evidence tiers and uncertainty.
- Bounded phenotype-level scenario variation with deterministic seeds.
- Temporal interpolation of abstract cardiac response states.
- A normalized `CardiacState` contract spanning imaging, functional, and omics features.
- Modality adapters that normalize already-processed measurements into the common contract.
- An explicit scenario-to-multimodal translation layer with versioned, inspectable coefficients.
- Baseline abnormality scoring.
- Nearest-known-state distance as a transparent OOD baseline.
- Domain attribution ranked by deviation from baseline.
- Multimodal recovery scoring with modality-specific and overall rescue estimates.
- A single end-to-end assessment pipeline for scenario → state → detection → attribution → recovery.
- Realism scoring that penalizes uncertainty and extrapolation.
- Hash-based audit records for reproducibility.
- Benchmark leakage checks for held-out scenarios.
- Automated tests and a Python 3.10–3.12 GitHub Actions matrix.

## Multimodal state layer

The common state representation keeps modalities separate while providing a merged namespace for benchmark evaluation:

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

See [`docs/MULTIMODAL.md`](docs/MULTIMODAL.md) for the contract and adapter philosophy.

## End-to-end API

The main computational flow is exposed through `cardivex.pipeline`:

```python
from cardivex.pipeline import assess_scenario, run_end_to_end

assessment = assess_scenario(
    scenario,
    baseline=healthy_state,
    known_states=reference_states,
)

result = run_end_to_end(
    scenario,
    baseline=healthy_state,
    known_states=reference_states,
    treated_state=treated_state,
)
```

The result keeps the full challenged multimodal state, detection/novelty scores, ranked domain attribution, and optional recovery estimates in one structured object.

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

The project is intentionally modular so future imaging, functional, transcriptomic, and ML implementations can consume the same scenario, cardiac-state, benchmark, pipeline, and audit contracts instead of inventing incompatible representations.
