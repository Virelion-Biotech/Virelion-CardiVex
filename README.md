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

- `cardivex/` — core scenario, variation, defense, realism, and audit logic.
- `schemas/` — machine-readable scenario definitions.
- `examples/` — example scenario objects.
- `docs/` — architecture, scenario specification, and validation rules.
- `tests/` — unit tests for core deterministic behavior.

## What the first implementation supports

- Typed scenario objects with evidence tiers and uncertainty.
- Bounded phenotype-level scenario variation with deterministic seeds.
- Temporal interpolation of abstract cardiac response states.
- Realism scoring that penalizes uncertainty and extrapolation.
- Baseline-distance abnormality scoring.
- Nearest-known-state distance as a simple OOD baseline.
- Recovery/rescue scoring relative to baseline.
- Hash-based audit records for reproducibility.
- Automated tests on Python 3.10–3.12.

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

The project is intentionally built so later imaging, functional, transcriptomic, and ML modules can consume the same scenario and audit contracts rather than inventing incompatible representations.
