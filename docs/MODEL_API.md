# CardiVex Model API

CardiVex separates model execution from benchmark definition. Any predictive model that implements the `CardiVexModel` contract can consume processed feature rows without changing the benchmark or provenance layer.

## Adapter contract

A model adapter exposes:

- `model_id`
- `model_version`
- `predict(feature_rows)` returning `ModelPrediction` objects

The adapter operates on processed features only. It does not define acquisition, wet-lab procedures, or biological-agent construction.

## CLI

After installation:

```text
cardivex run-model --model my_adapter:factory --input benchmark_input.json --output result.json
```

The input JSON must contain:

```json
{"feature_rows": [{"domain:inflammatory_activation": 0.4}]}
```

The output records the model identity, version, input count, and normalized predictions. This makes the same model runnable against future real-data, held-out, and external benchmarks.

## Intended progression

1. transparent baseline models
2. calibrated classical ML
3. multimodal predictive surrogates
4. externally supplied model adapters
5. prospective and independent validation
