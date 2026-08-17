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


_GSE144424_CONDITIONS = {
    "A": ("normoxia", 0.0),
    "B": ("hypoxia", 6.0),
    "C": ("reoxygenation_1", 12.0),
    "D": ("reoxygenation_2", 30.0),
}


def parse_gse144424_sample_title(sample_id: str, title: str) -> GEOSampleMetadata:
    """Parse the documented GSE144424 RNA-seq sample naming convention.

    Expected titles resemble ``18499_A_RNA-seq``. Replicate suffixes such as
    ``18511_2_A_RNA-seq`` remain tied to the same subject_id (18511).
    """
    match = re.fullmatch(r"(?P<subject>\d+)(?:_\d+)?_(?P<code>[ABCD])_RNA-seq", title.strip())
    if not match:
        raise ValueError(f"unsupported GSE144424 sample title: {title}")
    code = match.group("code")
    condition, elapsed_hours = _GSE144424_CONDITIONS[code]
    return GEOSampleMetadata(
        sample_id=sample_id,
        subject_id=match.group("subject"),
        condition_code=code,
        condition=condition,
        elapsed_hours=elapsed_hours,
        modality="rna_seq",
    )
