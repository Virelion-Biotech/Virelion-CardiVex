# Virelion-CardiVex

CardiVex is a computational challenge and evaluation platform for human cardiac models. It represents realistic, non-operational biological challenge states and evaluates whether analysis systems can detect abnormality, characterize affected biological systems, recognize unfamiliar states, quantify recovery, and reproduce every conclusion.

## Core question

> Can a human cardiac digital surrogate and defensive analysis system remain effective when a challenge produces an unusual or previously unseen phenotype?

## Platform

```text
Evidence / datasets
       |
       v
Empirical phenotype profiles
       |
       v
Scenario + challenge families
       |
       v
Benchmark manifest + leakage audit
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
      +----------+-----------+
      |                      |
      v                      v
 detection              novelty / OOD
      |                      |
      +----------+-----------+
                 |
                 v
        mechanism attribution
                 |
                 v
          modality scoring
                 |
                 v
        countermeasure test
                 |
                 v
          rescue scoring
                 |
                 v
      calibration + uncertainty
                 |
                 v
       audit + reproducibility
```

## Current implementation

- Typed scenarios with evidence tiers, uncertainty, provenance, and temporal states.
- Dataset/evidence registries and processed-observation ingestion.
- Dataset loaders, condition grouping, and quality gates.
- Empirical phenotype distributions with domain-level uncertainty.
- Evidence-linked scenario construction from empirical downstream states.
- Challenge families: familiar, severity-shift, temporal-shift, combinatorial, and held-out novel.
- Correlation estimation across observed phenotype domains.
- Benchmark manifests, split isolation, leakage detection, and novelty audits.
- A normalized `CardiacState` contract spanning imaging, functional, and omics measurements.
- Transparent scenario-to-multimodal translation profiles.
- End-to-end detection, OOD, and domain-attribution baselines.
- Modality-specific abnormality/novelty scoring and assessment summaries.
- Threshold calibration and uncertainty reporting.
- Countermeasure/recovery scoring.
- End-to-end benchmark suite execution with structured per-scenario results.
- Deterministic JSON serialization for benchmark artifacts.
- Hash-based audit records and reproducibility metadata.
- A transparent longitudinal predictive surrogate with experimental-unit leakage checks.
- Held-out temporal benchmarking against a persistence baseline.
- Automated tests and a Python 3.10–3.12 GitHub Actions matrix.

## End-to-end benchmark

```python
from cardivex.suite import run_benchmark_suite, build_run_audit
from cardivex.serialization import write_json

run = run_benchmark_suite(
    scenarios,
    baseline=healthy_state,
    known_states=reference_states,
)

audit = build_run_audit(run, run_id="RUN-001", seed=42)
write_json({"run": run, "audit": audit}, "artifacts/run.json")
```

The suite refuses to proceed when scenario definitions fail validation, when held-out scenarios directly leak development vectors, or when the held-out set fails the configured novelty audit.

See [`docs/END_TO_END_BENCHMARK.md`](docs/END_TO_END_BENCHMARK.md), [`docs/SCORING_AND_OUTPUTS.md`](docs/SCORING_AND_OUTPUTS.md), and [`docs/TEMPORAL_BENCHMARK.md`](docs/TEMPORAL_BENCHMARK.md).

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

## Scenario philosophy

CardiVex separates **scenario realism** from **scenario certainty**. A challenge can be deliberately unfamiliar while still being grounded in measured downstream host-response evidence. Generated states retain the source datasets and transformations used to construct them.

The challenge engine works at the level of measurable host-response phenotypes and temporal behavior. It does not encode procedural instructions for creating, modifying, optimizing, or deploying a biological agent.

## Validation ladder

```text
observed reference
       -> characterized proxy
       -> validated computational representation
       -> bounded synthetic variation
       -> held-out novel scenario
```

Claims become more exploratory as a scenario moves rightward. Held-out scenarios are kept separate from development inputs to prevent leakage.

## Development

```bash
pip install -e '.[test]'
pytest
```

The project is intentionally modular so future imaging, functional, transcriptomic, and ML implementations can consume the same scenario, cardiac-state, benchmark, evaluation, pipeline, and audit contracts instead of inventing incompatible representations.
