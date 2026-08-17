# Validated benchmark workflow

`run_validated_benchmark` is the integrated entry point for CardiVex evaluation.

It combines two deliberately separate layers:

1. **Defensive benchmark scoring** over the declared scenario suite.
2. **Surrogate validation** against disjoint held-out longitudinal experimental units.

The second layer does not use the held-out measurements to construct the scenario or tune the defensive thresholds. Its purpose is to test whether the representation itself remains consistent with unseen observations.

```text
Development evidence
      ↓
Empirical / bounded scenario
      ↓
Defensive benchmark ──────────┐
                              ↓
Disjoint held-out units → surrogate validation
                              ↓
                    integrated audit artifact
```

A successful run therefore does **not** mean the surrogate is biologically validated. It means the declared benchmark and held-out validation protocol executed without split overlap and produced reproducible metrics. Scientific validation still requires independently curated data and a predeclared acceptance criterion.
