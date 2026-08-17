# CardiVex Challenge Factories

CardiVex now distinguishes several benchmark families so a detector is not evaluated only on random perturbations.

## Families

- **Familiar** — scenarios represented in the reference library.
- **Severity shift** — a characterized downstream phenotype with bounded magnitude change.
- **Temporal shift** — the same phenotype with bounded timing changes.
- **Combinatorial** — a new combination of individually characterized downstream phenotype profiles.
- **Held-out novel** — states excluded from model development and reserved for unfamiliar-state evaluation.

## Generation rule

Factories operate on downstream phenotype representations and preserve source-dataset lineage. They do not encode procedures for generating an initiating biological agent.

Every generated scenario retains:

- source dataset identifiers;
- transformation history;
- evidence tier;
- confidence;
- OOD status;
- temporal trajectory;
- validation targets.

## Benchmark construction

A benchmark should contain separate train/development and held-out scenario groups. `cardivex.benchmark_factory.audit_manifest()` checks exact leakage and tests whether held-out states remain separated from known scenario vectors.

## Interpretation

Generated scenarios are computational hypotheses until validated against independent observations. The benchmark should report family, evidence tier, novelty distance, and validation status alongside model performance.
