from __future__ import annotations

import pytest

from cardivex.physiology_linkage import (
    PhysiologyLink,
    audit_physiology_linkage,
    group_level_comparison_allowed,
    require_sample_level_ready,
)


def test_complete_one_to_one_linkage_is_sample_level_ready():
    audit = audit_physiology_linkage(
        ["S1", "S2"],
        ["U1", "U2"],
        [
            PhysiologyLink("S1", "U1", "2D", "source:1"),
            PhysiologyLink("S2", "U2", "3D", "source:2"),
        ],
    )
    assert audit.status == "sample_paired"
    require_sample_level_ready(audit)


def test_missing_links_block_sample_level_analysis_but_allow_group_level_description():
    audit = audit_physiology_linkage(["S1", "S2"], ["U1", "U2"], [])
    assert audit.status == "unpaired"
    assert not audit.sample_level_ready
    assert group_level_comparison_allowed(audit, same_condition_labels=True)
    with pytest.raises(ValueError, match="explicit one-to-one"):
        require_sample_level_ready(audit)


def test_duplicate_pairing_is_rejected():
    audit = audit_physiology_linkage(
        ["S1"],
        ["U1"],
        [
            PhysiologyLink("S1", "U1", "3D", "source:1"),
            PhysiologyLink("S1", "U1", "3D", "source:2"),
        ],
    )
    assert audit.status == "invalid_duplicate_linkage"
    assert audit.duplicate_rna == ("S1",)
