# CardiVex Scenario Specification

A CardiVex scenario is a structured representation of a plausible cardiac challenge state. It is designed to answer defensive questions about detection, abnormality recognition, affected biological systems, novelty, recovery, and reproducibility.

## Scenario object

Each scenario should define:

- `scenario_id`: stable identifier
- `version`: semantic scenario version
- `name`: concise human-readable label
- `description`: high-level scenario description
- `target_model`: cardiac model class
- `evidence`: references or dataset identifiers supporting the represented host-response features
- `evidence_tier`: observed, characterized_proxy, validated_model, or extrapolated
- `confidence`: high, moderate, or exploratory
- `phenotype_domains`: measurable affected domains
- `temporal_profile`: onset, peak, persistence, and recovery characteristics
- `severity_profile`: bounded domain-level severity values
- `interaction_profile`: documented or model-derived relationships among domains
- `variation_space`: permitted synthetic variation around validated values
- `validation_targets`: measurements that should agree with the scenario
- `ood_status`: whether the scenario is held out for novelty testing
- `provenance`: source and transformation history

## Evidence tiers

### observed
Directly measured in an appropriate experimental or observational dataset.

### characterized_proxy
Measured in a safer or more controlled proxy that is intended to reproduce selected host-response dimensions.

### validated_model
A computational representation that has been quantitatively checked against held-out observations.

### extrapolated
A hypothetical state produced by bounded modeling beyond the available observations. Extrapolated scenarios must not be presented as experimentally established facts.

## Phenotype domains

CardiVex uses domain-level effects rather than an initiating-agent recipe. Initial domains may include:

- inflammatory activation
- endothelial/vascular dysfunction
- metabolic stress
- mitochondrial dysfunction
- oxidative stress
- viability/cell-death burden
- structural disorganization
- fibrosis/remodeling tendency
- contractile impairment
- electrophysiologic disturbance

Values are normalized model features, not biological instructions.

## Temporal representation

A scenario may be represented as a sequence of states:

```text
baseline -> onset -> acute -> evolving -> peak -> recovery
```

Each state can contain domain values and uncertainty intervals. Temporal behavior should be preserved when the source evidence supports it.

## Realism score

CardiVex should compute a scenario realism score from evidence coverage, validation agreement, temporal agreement, and extrapolation burden. The score is a research-quality indicator, not a claim that a scenario predicts a real event.

Recommended components:

```text
realism = weighted(
  evidence_coverage,
  phenotype_agreement,
  temporal_agreement,
  functional_agreement,
  uncertainty_penalty,
  extrapolation_penalty
)
```

## Challenge classes

### Familiar
Scenario represented in the training/evaluation library.

### Combinatorial
Uses individually characterized domains in a new combination.

### Temporal-shift
Uses a validated response with a previously unseen timing pattern within bounded limits.

### Severity-shift
Uses a validated phenotype with a new severity profile within the supported range.

### Novel-state
A held-out state designed to test whether the system can recognize abnormality without requiring a known class label.

## Benchmark rule

Training data must never contain the exact held-out scenario definition, its derived feature vector, or a direct transformed copy of its measurements.

## Safety boundary

Scenario files may specify measurable host-response features, temporal behavior, uncertainty, validation evidence, and computational transformations. They must not contain procedural instructions for creating, culturing, modifying, optimizing, or deploying a biological agent.
