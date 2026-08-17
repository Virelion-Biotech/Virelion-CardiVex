import pytest

from cardivex.model_registry import ModelRecord, ModelRegistry


def test_model_registry_is_deterministic_and_provenance_friendly():
    registry = ModelRegistry([
        ModelRecord("M-2", "centroid", "1.0", "cardivex-v1", "train"),
        ModelRecord("M-1", "baseline", "1.0", "cardivex-v1", "train"),
    ])
    assert tuple(r.model_id for r in registry.all()) == ("M-1", "M-2")
    assert registry.get("M-2").training_split == "train"


def test_model_registry_rejects_duplicates():
    record = ModelRecord("M-1", "baseline", "1.0", "cardivex-v1", "train")
    with pytest.raises(ValueError):
        ModelRegistry([record, record])
