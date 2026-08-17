import csv
from pathlib import Path

import pytest

from cardivex.dataset import assemble_batch, split_by_condition
from cardivex.ingest import ingest_processed_observation
from cardivex.loader import load_csv, records_from_rows
from cardivex.quality import inspect_records, require_clean


def make_record(observation_id: str, condition: str = "baseline"):
    return ingest_processed_observation(
        observation_id=observation_id,
        dataset_id="DS-0001",
        condition=condition,
        time=0,
        domain_scores={"inflammatory_activation": 0.1},
        imaging={"morphology": 0.2},
        functional={"contractility": 0.3},
        source_ref="example://obs",
    )


def test_rows_decode_feature_json():
    rows = [{
        "observation_id": "OBS-1",
        "dataset_id": "DS-0001",
        "condition": "challenge",
        "time": "2",
        "domain_scores": '{"inflammatory_activation": 0.8}',
        "functional": '{"contractility": 0.7}',
    }]
    records = records_from_rows(rows)
    assert records[0].state.functional.values["contractility"] == 0.7


def test_csv_loader(tmp_path: Path):
    path = tmp_path / "obs.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["observation_id", "dataset_id", "condition", "time", "domain_scores"])
        writer.writeheader()
        writer.writerow({"observation_id": "OBS-1", "dataset_id": "DS-0001", "condition": "baseline", "time": 0, "domain_scores": '{"a": 0.1}'})
    records = load_csv(path)
    assert len(records) == 1


def test_dataset_condition_split():
    batch = assemble_batch("DS-0001", [make_record("OBS-1"), make_record("OBS-2", "challenge")])
    groups = split_by_condition(batch, ["baseline", "challenge"])
    assert len(groups["baseline"].records) == 1
    assert len(groups["challenge"].records) == 1


def test_quality_flags_duplicate_observation():
    records = [make_record("OBS-1"), make_record("OBS-1")]
    issues = inspect_records(records)
    assert any(i.code == "DUPLICATE_OBSERVATION" for i in issues)
    with pytest.raises(ValueError):
        require_clean(records)


def test_quality_allows_warning_only():
    record = ingest_processed_observation(
        observation_id="OBS-2",
        dataset_id="DS-0001",
        condition="baseline",
        time=0,
        domain_scores={"a": 0.1},
        imaging={"morphology": 0.2},
    )
    require_clean([record])
