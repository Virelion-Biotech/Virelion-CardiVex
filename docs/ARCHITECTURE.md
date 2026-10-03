# CardiVex Architecture

CardiVex is a computational challenge and evaluation platform for human cardiac models. Its purpose is to represent realistic, non-operational biological challenge states, test detection and characterization systems against both familiar and unfamiliar phenotypes, and quantify recovery toward baseline.

## System model

```text
Scenario registry
      |
      v
Scenario evidence + assumptions
      |
      v
Scenario translation layer
      |
      v
Cardiac digital surrogate
      |
      +-------------------------+
      |                         |
      v                         v
Observed/proxy state      Synthetic variation
      |                         |
      +------------+------------+
                   v
          Multimodal measurements
        /          |           \
    imaging      omics       function
        \          |           /
                   v
        Detection + characterization
             /             \
            v               v
        known-state       OOD / novel-state
            |                 |
            +--------+--------+
                     v
             Countermeasure test
                     |
                     v
              Recovery scoring
                     |
                     v
              Audit + provenance
```

## Design principles

1. **Scenario realism is evidence-led.** A challenge should trace to observations, characterized proxies, validated datasets, or explicitly labeled extrapolation.
2. **The platform models effects, not operational generation of biological agents.** Scenario definitions describe host-response states, timing, severity, and phenotype relationships rather than procedures for creating an initiating agent.
3. **Normal biological variability is part of the benchmark.** Donor, batch, maturation, imaging, and technical variation must be represented so that abnormality detection is not equivalent to detecting any deviation from a single reference.
4. **Unknown states are first-class test cases.** The system must support out-of-distribution evaluation rather than forcing every phenotype into a known class.
5. **Mechanistic outputs are separate from detection outputs.** A model may detect an abnormal state without correctly identifying its affected cellular systems; these claims are evaluated independently.
6. **Countermeasure claims require recovery evidence.** Computational rescue scores are evaluations of movement toward baseline and are not, by themselves, proof of efficacy.
7. **Every conclusion is reproducible.** Scenario version, data version, model version, feature pipeline, configuration, seed, and provenance are recorded for every run.

## Core modules

### Scenario registry
Stores structured scenario definitions, evidence links, confidence levels, assumptions, phenotype domains, temporal behavior, and validation status.

### Scenario translation layer
Maps scenario-level descriptions into measurable host-response domains such as inflammatory state, vascular dysfunction, metabolic stress, structural remodeling, viability, and cardiac function.

### Cardiac digital surrogate
Represents the measurable state of an iPSC-derived cardiac model using multimodal features. It supports observed measurements, experimentally characterized proxies, and synthetic variation.

### Challenge engine
Generates bounded perturbations around validated states, including novel combinations, severity shifts, and temporal patterns. Generated states retain lineage to the evidence and assumptions from which they were derived.

### Defensive AI engine
Supports:

- baseline/stressed classification
- abnormality scoring
- phenotype-domain attribution
- uncertainty estimation
- out-of-distribution detection
- calibration and threshold analysis

### Countermeasure evaluator
Compares challenged and treated states against baseline across structural, functional, viability, and molecular dimensions.

### Audit layer
Produces immutable run metadata and a machine-readable explanation of how each result was produced.

## Validation ladder

```text
Observed reference
      -> characterized proxy
      -> validated computational representation
      -> bounded synthetic variation
      -> held-out novel scenario
```

The closer a scenario is to the right side of the ladder, the more explicitly its uncertainty must be reported.
