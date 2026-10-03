# Virelion-CardiVex

CardiVex is a Python evaluation framework for cardiac challenge scenarios. It represents phenotype-level challenge states and evaluates detection, characterization, novelty/OOD behavior, recovery, uncertainty, and reproducibility.

## What it contains

- Typed challenge scenarios with provenance and uncertainty.
- Empirical phenotype distributions and processed-observation ingestion.
- Familiar, severity-shift, temporal-shift, combinatorial, and held-out novel challenge families.
- Benchmark manifests, split isolation, leakage checks, and novelty audits.
- A normalized `CardiacState` representation for imaging, functional, and omics measurements.
- Detection and OOD baselines.
- Modality-specific scoring and domain attribution.
- Threshold calibration and uncertainty reporting.
- Recovery/countermeasure scoring.
- Longitudinal predictive baselines and temporal benchmarks.
- Deterministic benchmark artifacts and run audits.

## Installation

```bash
pip install -e '.[test]'
pytest
```

## Usage

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

## Inputs and outputs

**Inputs:** phenotype-level challenge scenarios, empirical phenotype distributions or processed observations, baseline/reference states, benchmark manifests, split definitions, and model/surrogate outputs.

**Outputs:** detection and OOD scores, characterization/attribution results, uncertainty and calibration summaries, recovery scores, temporal benchmark results, deterministic benchmark artifacts, and run audits.

Development/calibration data must remain separate from final held-out scenarios.

## Validation

The validation ladder distinguishes observed reference data, characterized proxies, computational representations, synthetic variations, and held-out scenarios. Benchmark manifests include split isolation, leakage checks, and novelty audits. Software tests should be run with `pytest`.

## Limitations

Scenario realism is not equivalent to biological validity. Held-out novelty depends on benchmark construction and must be independently audited. Model performance depends on feature representation, calibration data, and split policy. Synthetic scenarios cannot substitute for empirical validation.

## License

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See `LICENSE`.
