# Surrogate validation

A generated cardiac surrogate is not considered realistic merely because it resembles a development distribution. CardiVex therefore separates three questions:

1. **Development fit** — does the construction reproduce patterns used to build it?
2. **Held-out agreement** — does it agree with observations from experimental units not used during construction?
3. **Cross-dataset generalization** — does the behavior persist when the held-out observations come from a different dataset or acquisition context?

## Validation unit

For longitudinal data, an experimental unit is kept together across time. Splitting individual time points across development and evaluation is leakage.

## Metrics

`SurrogateValidation` reports domain-level MAE and maximum absolute error plus trajectory-level similarity. Results remain grouped by experimental unit rather than pooling all time points as independent samples.

## Interpretation

A low held-out error supports representation fidelity, not causal validity. A generated state remains extrapolated until independently validated.

The validation API intentionally operates on downstream phenotype and measured multimodal observations; it does not encode procedural instructions for producing a biological challenge.
