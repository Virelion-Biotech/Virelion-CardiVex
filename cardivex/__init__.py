"""CardiVex: computational cardiac challenge and defensive evaluation."""

from .models import Scenario, ScenarioState, EvidenceTier, Confidence
from .engine import generate_variations, interpolate_timeline
from .realism import realism_score
from .audit import build_audit_record

__all__ = [
    "Scenario",
    "ScenarioState",
    "EvidenceTier",
    "Confidence",
    "generate_variations",
    "interpolate_timeline",
    "realism_score",
    "build_audit_record",
]
