from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Sequence

from .model_api import CardiVexModel, validate_model_predictions


def _load_model(spec: str) -> CardiVexModel:
    if ":" not in spec:
        raise ValueError("model must use module:attribute notation")
    module_name, attribute_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    model = getattr(module, attribute_name)()
    for attr in ("model_id", "model_version", "predict"):
        if not hasattr(model, attr):
            raise TypeError(f"model adapter is missing required attribute: {attr}")
    return model


def run_model(*, model: CardiVexModel, input_path: Path, output_path: Path) -> None:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    rows = payload.get("feature_rows")
    if not isinstance(rows, list):
        raise ValueError("input JSON must contain a feature_rows list")
    predictions = tuple(model.predict(rows))
    validate_model_predictions(predictions, expected_count=len(rows))
    output = {
        "model_id": model.model_id,
        "model_version": model.model_version,
        "input_count": len(rows),
        "predictions": [
            {
                "label": item.label,
                "score": float(item.score),
                "metadata": dict(item.metadata),
            }
            for item in predictions
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, sort_keys=True, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cardivex", description="Run predictive models against CardiVex processed benchmarks.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run-model", help="run a CardiVex model adapter on processed feature rows")
    run.add_argument("--model", required=True, help="Python adapter as module:factory")
    run.add_argument("--input", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run-model":
        run_model(model=_load_model(args.model), input_path=args.input, output_path=args.output)
        return 0
    raise RuntimeError("unsupported command")
