# Virelion-CardiVex

CardiVex is a Python evaluation framework for cardiac challenge scenarios. It represents phenotype-level challenge states and evaluates detection, characterization, novelty/OOD behavior, recovery, uncertainty, and reproducibility.

## Scope

CardiVex provides:

- typed challenge scenarios with provenance and uncertainty;
- empirical phenotype distributions and processed-observation ingestion;
- familiar, severity-shift, temporal-shift, combinatorial, and held-out novel challenge families;
- benchmark manifests, split isolation, leakage checks, and novelty audits;
- a normalized `CardiacState` representation for imaging, functional, and omics measurements;
- detection and OOD baselines;
- modality-specific scoring and domain attribution;
- threshold calibration and uncertainty reporting;
- recovery/countermeasure scoring;
- longitudinal predictive baselines and temporal benchmarks;
- deterministic benchmark artifacts and run audits.

## Benchmark workflow

```text
empirical evidence
      ↓
phenotype profiles
      ↓
scenario construction
      ↓
benchmark manifest / leakage audit
      ↓
model or surrogate
      ↓
detection / OOD / attribution
      ↓
calibration and uncertainty
      ↓
held-out evaluation
```

Development and calibration data must remain separate from final held-out scenarios.

## Integration with CardiAgent

CardiAgent can create blinded challenge handoffs. CardiVex receives the observable representation and returns outcome-level information. Ground truth remains outside the blinded presentation until scoring.

## Scenario boundary

Scenarios represent measurable host-response phenotypes and temporal behavior. The repository does not provide procedural instructions for creating, modifying, optimizing, or deploying biological agents.

## Installation

```bash
pip install -e '.[test]'
pytest
```

## Example

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

## Validation ladder

Observed reference data should be distinguished from derived proxies and synthetic variations:

```text
observed → characterized proxy → computational representation → synthetic variation → held-out scenario
```

Interpretation becomes more model-dependent as the representation moves away from observed data.

## Limitations

Scenario realism is not equivalent to biological validity. Held-out novelty is a property of the benchmark construction and must be independently audited. Model performance depends on the feature representation, calibration data, and split policy.

## License

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See `LICENSE`.

## Citation

Cite the repository release and the empirical datasets/publications used to construct benchmark scenarios.
