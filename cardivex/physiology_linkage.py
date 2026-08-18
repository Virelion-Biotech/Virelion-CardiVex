from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class PhysiologyLink:
    """Explicit mapping between an RNA observation and a physiology unit."""

    rna_sample_id: str
    physiology_unit_id: str
    condition: str
    source_ref: str


@dataclass(frozen=True)
class PhysiologyLinkageAudit:
    """Audit result for deciding whether RNA/physiology analysis is sample-paired."""

    status: str
    rna_sample_count: int
    physiology_unit_count: int
    linked_pair_count: int
    unmatched_rna: tuple[str, ...]
    unmatched_physiology: tuple[str, ...]
    duplicate_rna: tuple[str, ...]
    duplicate_physiology: tuple[str, ...]

    @property
    def sample_level_ready(self) -> bool:
        return self.status == "sample_paired"


def audit_physiology_linkage(
    rna_sample_ids: Sequence[str],
    physiology_unit_ids: Sequence[str],
    links: Sequence[PhysiologyLink],
) -> PhysiologyLinkageAudit:
    """Audit explicit RNA↔physiology pairing without inferring links from names."""
    rna = tuple(rna_sample_ids)
    physiology = tuple(physiology_unit_ids)
    rna_set = set(rna)
    physiology_set = set(physiology)

    seen_rna: dict[str, int] = {}
    seen_physiology: dict[str, int] = {}
    for link in links:
        seen_rna[link.rna_sample_id] = seen_rna.get(link.rna_sample_id, 0) + 1
        seen_physiology[link.physiology_unit_id] = seen_physiology.get(link.physiology_unit_id, 0) + 1
        if link.rna_sample_id not in rna_set:
            raise ValueError(f"link references unknown RNA sample: {link.rna_sample_id}")
        if link.physiology_unit_id not in physiology_set:
            raise ValueError(f"link references unknown physiology unit: {link.physiology_unit_id}")

    duplicate_rna = tuple(sorted(sample for sample, count in seen_rna.items() if count > 1))
    duplicate_physiology = tuple(sorted(unit for unit, count in seen_physiology.items() if count > 1))
    linked_rna = set(seen_rna)
    linked_physiology = set(seen_physiology)
    unmatched_rna = tuple(sorted(rna_set - linked_rna))
    unmatched_physiology = tuple(sorted(physiology_set - linked_physiology))

    if duplicate_rna or duplicate_physiology:
        status = "invalid_duplicate_linkage"
    elif len(rna) == len(physiology) and not unmatched_rna and not unmatched_physiology and len(links) == len(rna):
        status = "sample_paired"
    elif links:
        status = "partial_linkage"
    else:
        status = "unpaired"

    return PhysiologyLinkageAudit(
        status=status,
        rna_sample_count=len(rna),
        physiology_unit_count=len(physiology),
        linked_pair_count=len(links),
        unmatched_rna=unmatched_rna,
        unmatched_physiology=unmatched_physiology,
        duplicate_rna=duplicate_rna,
        duplicate_physiology=duplicate_physiology,
    )


def require_sample_level_ready(audit: PhysiologyLinkageAudit) -> None:
    """Refuse sample-level RNA→physiology analysis unless pairing is explicit and complete."""
    if not audit.sample_level_ready:
        raise ValueError(
            "sample-level RNA-to-physiology analysis is blocked until explicit one-to-one "
            f"experimental-unit linkage is supplied; current status={audit.status}"
        )


def group_level_comparison_allowed(audit: PhysiologyLinkageAudit, *, same_condition_labels: bool) -> bool:
    """Permit only descriptive group-level comparison when sample pairing is unavailable."""
    return audit.status in {"unpaired", "partial_linkage"} and same_condition_labels


def linkage_contract() -> Mapping[str, object]:
    """Machine-readable contract used by the GSE234907 physiology audit."""
    return {
        "sample_level_requirement": "explicit one-to-one RNA sample ↔ physiology experimental-unit mapping",
        "forbidden_inference": "do not infer pairing from 2D/3D class labels, order, or filenames",
        "allowed_without_pairing": "group-level descriptive comparison with explicit caveat",
        "required_source_fields": ["rna_sample_id", "physiology_unit_id", "condition", "source_ref"],
    }
