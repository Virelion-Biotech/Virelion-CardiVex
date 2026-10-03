# End-to-End Benchmark Execution

CardiVex now exposes a single benchmark runner that connects scenario validation, split isolation, defensive assessment, novelty auditing, and reproducibility metadata.

## Execution flow

```text
Scenario objects
      |
      v
Manifest validation
      |
      v
Benchmark split validation
      |
      +----------------------------+
      |                            |
      v                            v
Development states           Held-out novel states
      |                            |
      +-------------+--------------+
                    v
             defensive baseline
                    |
             +------+------+
             |             |
          abnormality     OOD
             |             |
             +------+------+
                    v
               attribution
                    |
                    v
              run summary
                    |
                    v
             audit record
```

## Main API

```python
from cardivex.suite import run_benchmark_suite

run = run_benchmark_suite(
    scenarios,
    baseline=healthy_state,
    known_states=reference_states,
)

summary = run.to_dict()
```

`build_run_audit()` adds a content digest and the versions/configuration needed to reproduce the run.

## Failure behavior

The suite refuses to run when:

- scenario definitions fail validation;
- scenario IDs overlap between benchmark splits;
- held-out scenarios directly duplicate development phenotype vectors;
- held-out scenarios fail the configured novelty threshold.

Per-scenario runtime failures are retained as structured results rather than silently discarded.

## Scientific interpretation

The runner is an evaluation harness, not evidence that a generated scenario predicts a real event. Generated challenge states remain labeled according to their evidence tier and transformation lineage. The suite evaluates downstream phenotype detection and generalization only.
