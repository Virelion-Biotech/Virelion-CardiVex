from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class GEOSampleMetadata:
    sample_id: str
    subject_id: str
    condition_code: str
    condition: str
    elapsed_hours: float
    modality: str
    replicate_index: int | None = None


_GSE144424_CONDITIONS = {
    "A": ("normoxia", 0.0),
    "B": ("hypoxia", 6.0),
    "C": ("reoxygenation_1", 12.0),
    "D": ("reoxygenation_2", 30.0),
}


def parse_gse144424_sample_title(sample_id: str, title: str) -> GEOSampleMetadata:
    """Parse the documented GSE144424 RNA-seq sample naming convention."""
    match = re.fullmatch(r"(?P<subject>\d+)(?:_(?P<replicate>\d+))?_(?P<code>[ABCD])_RNA-seq", title.strip())
    if not match:
        raise ValueError(f"unsupported GSE144424 sample title: {title}")
    return _metadata_from_parts(
        sample_id=sample_id,
        subject_id=match.group("subject"),
        code=match.group("code"),
        replicate_index=int(match.group("replicate")) if match.group("replicate") else None,
    )


def parse_gse144424_count_column(sample_id: str) -> GEOSampleMetadata:
    """Parse the processed-count column convention, e.g. ``H18511_2_A``."""
    match = re.fullmatch(r"H(?P<subject>\d+)(?:_(?P<replicate>\d+))?_(?P<code>[ABCD])", sample_id.strip())
    if not match:
        raise ValueError(f"unsupported GSE144424 count column: {sample_id}")
    return _metadata_from_parts(
        sample_id=sample_id,
        subject_id=match.group("subject"),
        code=match.group("code"),
        replicate_index=int(match.group("replicate")) if match.group("replicate") else None,
    )


def _metadata_from_parts(*, sample_id: str, subject_id: str, code: str, replicate_index: int | None) -> GEOSampleMetadata:
    try:
        condition, elapsed_hours = _GSE144424_CONDITIONS[code]
    except KeyError as exc:
        raise ValueError(f"unsupported GSE144424 condition code: {code}") from exc
    return GEOSampleMetadata(
        sample_id=sample_id,
        subject_id=subject_id,
        condition_code=code,
        condition=condition,
        elapsed_hours=elapsed_hours,
        modality="rna_seq",
        replicate_index=replicate_index,
    )
