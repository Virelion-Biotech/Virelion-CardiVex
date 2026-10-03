# Shared cardiac state simulator

CardiVex now has a first shared perturbation-to-phenotype layer. It is deliberately a **normalized computational phenotype model**, not a clinical-grade electrophysiology or hemodynamics solver.

```text
Patient profile
      |
      v
healthy latent state
      |
      v
mechanism-level perturbation vector
      |
      v
shared latent cardiac state
      |
      +-------------------------------+
      |               |               |
      v               v               v
    ECG          hemodynamics       motion
      |                               |
      +---------------+---------------+
                      v
                 biomarkers
```

## Shared latent state

The current state contains:

- contractility
- electrical instability
- vascular dysfunction
- metabolic stress
- inflammatory activation
- structural remodeling
- tissue injury
- ischemic burden

The existing CardiVex domain representation is generated from the same state, so the simulator can feed the established scoring and benchmark stack rather than creating a second incompatible representation.

## Perturbation interface

Perturbations are mechanism-level normalized burdens:

```python
{
    "ischemia": 0.8,
    "inflammation": 0.4,
    "electrophysiology": 0.2,
    "injury": 0.3,
    "pathogen_host_response": 0.5,
    "metabolic": 0.2,
    "genetic_susceptibility": 0.1,
}
```

The host-response representation intentionally does not encode procedures, agent construction, optimization, or deployment instructions.

## Observation model

`observe_state()` maps the latent state into normalized proxies for ECG, pressure/volume and output measures, regional/global motion, and biomarkers. A seeded measurement-noise layer prevents the downstream AI from relying on perfectly deterministic observations.

All outputs are currently bounded to `[0, 1]` because the existing CardiVex state contract uses normalized feature values. Real-unit calibration should be added only when validated reference datasets support it.

## Current scope and next validation step

This is the first implementation milestone:

**healthy baseline → shared perturbation state → ECG + hemodynamic proxies + motion + biomarkers.**

The next scientific step is not to add seven more hand-written disease models. It is to calibrate the parameter mappings against empirical data, quantify uncertainty, and test whether distinct perturbations can generate overlapping but mechanistically distinguishable multimodal phenotypes.
