# Evidence-calibrated multimodal translation

The default translation profile is intentionally hand-specified and should be treated as a prototype. CardiVex now also provides `fit_translation_profile()` for matched processed observations that contain both domain scores and one or more multimodal measurements.

The calibration layer computes transparent positive associations between each phenotype domain and each observed modality feature, then normalizes those associations into feature-specific weights. This is a descriptive surrogate mapping, not a causal model.

Recommended workflow:

```text
matched observations
        -> domain scores + imaging/function/omics
        -> association calibration
        -> TranslationProfile
        -> scenario_to_multimodal()
        -> held-out validation
```

The learned profile must be fitted only on development/calibration data. Held-out observations must remain isolated until prospective evaluation.

The calibration result retains sample count and dataset provenance so the profile can be traced back to the observations that informed it.
