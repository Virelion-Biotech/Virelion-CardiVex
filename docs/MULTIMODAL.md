# Multimodal Cardiac State Layer

CardiVex uses one normalized `CardiacState` contract for downstream imaging, functional, and omics measurements. Each modality remains independently named and is merged into a deterministic feature namespace.

## State model

```text
Scenario -> domain phenotype -> translation
                     |
        +------------+------------+
        |            |            |
      imaging     functional    omics
        +------------+------------+
                     |
                CardiacState
                     |
          detection / novelty /
             attribution
                     |
                  recovery
```

## Translation layer

`cardivex.translation` provides an explicit, inspectable mapping from scenario domain scores to normalized downstream feature groups. The default mapping is a **starter surrogate**, not an empirically validated biological model. Its coefficients should be calibrated against measured data before scientific conclusions are drawn.

CardiVex preserves the translation profile version in downstream metadata so evidence-calibrated replacements can be introduced without changing the scenario contract.

## Feature namespaces

- `imaging:<feature>`
- `functional:<feature>`
- `omics:<feature>`
- `domain:<phenotype_domain>`

This prevents collisions between similarly named variables across modalities.

## Defensive assessment

`cardivex.pipeline.assess_scenario()` performs a deterministic end-to-end pass:

1. translate a scenario into a multimodal state;
2. compare domain scores against baseline;
3. compare against known reference states for a simple OOD distance;
4. rank affected domains by deviation from baseline;
5. return the full challenged state for downstream models.

`run_end_to_end()` optionally adds recovery evaluation against a treated state.

## Interpretation limits

The starter detector is a benchmark primitive, not a trained classifier. Attribution ranks deviations and does not establish causality. Recovery scores quantify movement toward a selected baseline and do not prove efficacy.

Advanced representation learning, calibration, multimodal fusion, and empirically derived mappings can be added later without changing the scenario contract.
