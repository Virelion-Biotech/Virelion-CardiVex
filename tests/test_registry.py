import pytest

from cardivex.registry import DatasetRecord, DatasetRegistry, EvidenceRecord, EvidenceRegistry


def test_evidence_registry_is_deterministic():
    registry = EvidenceRegistry([
        EvidenceRecord("EV-2", "dataset", "ref-b", "B"),
        EvidenceRecord("EV-1", "dataset", "ref-a", "A"),
    ])
    assert [item.evidence_id for item in registry.all()] == ["EV-1", "EV-2"]


def test_dataset_registry_filters_conditions():
    registry = DatasetRegistry([
        DatasetRecord("DS-0001", "A", "human", "cardiac", ("imaging",), ("baseline",), "x"),
        DatasetRecord("DS-0002", "B", "human", "cardiac", ("omics",), ("challenge",), "y"),
    ])
    assert [item.dataset_id for item in registry.by_condition("challenge")] == ["DS-0002"]


def test_duplicate_ids_rejected():
    registry = EvidenceRegistry()
    record = EvidenceRecord("EV-1", "dataset", "ref", "test")
    registry.add(record)
    with pytest.raises(ValueError, match="duplicate evidence_id"):
        registry.add(record)
