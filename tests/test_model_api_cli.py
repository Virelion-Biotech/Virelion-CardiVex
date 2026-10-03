import json
from pathlib import Path

import pytest

from cardivex.cli import main
from cardivex.model_api import ModelPrediction, validate_model_predictions


def test_prediction_validation():
    validate_model_predictions([ModelPrediction("normal", 0.5)], expected_count=1)
    with pytest.raises(ValueError, match="score"):
        validate_model_predictions([ModelPrediction("normal", 1.2)], expected_count=1)
    with pytest.raises(ValueError, match="predictions"):
        validate_model_predictions([], expected_count=1)


def test_cli_runs_model_adapter(tmp_path: Path, monkeypatch):
    module = tmp_path / "toy_model.py"
    module.write_text(
        "from cardivex.model_api import ModelPrediction\n"
        "class Model:\n"
        "    model_id='toy'\n"
        "    model_version='1'\n"
        "    def predict(self, rows):\n"
        "        return [ModelPrediction('normal', 0.5) for _ in rows]\n"
        "def factory(): return Model()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps({"feature_rows": [{"domain:x": 0.2}, {"domain:x": 0.8}]}), encoding="utf-8")

    assert main([
        "run-model",
        "--model", "toy_model:factory",
        "--input", str(input_path),
        "--output", str(output_path),
    ]) == 0
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["model_id"] == "toy"
    assert result["input_count"] == 2
    assert len(result["predictions"]) == 2
