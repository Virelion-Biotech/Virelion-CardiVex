import pytest

from cardivex.dataset_qualification import qualify_records
from cardivex.ingest import ingest_processed_observation


def _records(modalities=True):
    rows = []
    for unit in ("U1", "U2"):
        for idx, value in enumerate((0.0, 0.4)):
            rows.append(
                ingest_processed_observation(
                    observation_id=f"{unit}-{idx}",
                    dataset_id="DS-Q",
                    condition="challenge",
                    time=float(idx),
                    domain_scores={"inflammatory_activation": value},
                    imaging={"structural_disorganization": value} if modalities else None,
                    functional={"contractile_impairment": value} if modalities else None,
                    omics={"inflammatory_signature": value} if modalities else None,
                    source_ref="fixture",
                )
            )
            record = rows[-1]
            rows[-1] = type(record)(
                observation_id=record.observation_id,
                dataset_id=record.dataset_id,
                condition=record.condition,
                time=record.time,
                state=type(record.state)(
                    imaging=record.state.imaging,
                    functional=record.state.functional,
                    omics=record.state.omics,
                    domain_scores=record.state.domain_scores,
                    time=record.state.time,
                    metadata={**record.state.metadata, "experimental_unit_id": unit},
                ),
                available_modalities=record.available_modalities,
                source_ref=record.source_ref,
            )
    return rows


def test_qualifies_complete_multimodal_longitudinal_dataset():
    result = qualify_records(_records(), required_modalities=("imaging", "functional", "omics"), expected_times=(0.0, 1.0))
    assert result.usable
    assert result.longitudinal_coverage == 1.0
    assert "multimodal_calibration" in result.recommended_uses
    assert "longitudinal_surrogate_validation" in result.recommended_uses


def test_rejects_missing_required_modality():
    result = qualify_records(_records(modalities=False), required_modalities=("imaging",))
    assert not result.usable
    assert "MISSING_REQUIRED_MODALITY:imaging" in result.issues


def test_requires_single_dataset():
    records = _records()
    other = records[0]
    records[0] = type(other)(
        observation_id=other.observation_id,
        dataset_id="DS-OTHER",
        condition=other.condition,
        time=other.time,
        state=other.state,
        available_modalities=other.available_modalities,
        source_ref=other.source_ref,
    )
    with pytest.raises(ValueError, match="exactly one dataset"):
        qualify_records(records)
