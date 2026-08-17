"""CardiVex: computational cardiac challenge and defensive evaluation."""

from .models import Scenario, ScenarioState, EvidenceTier, Confidence
from .engine import generate_variations, interpolate_timeline
from .realism import realism_score
from .defense import abnormality_score, nearest_state_distance, rescue_score
from .audit import build_audit_record
from .validation import validate_scenario, detect_direct_leakage

__all__ = [
    "Scenario",
    "ScenarioState",
    "EvidenceTier",
    "Confidence",
    "generate_variations",
    "interpolate_timeline",
    "realism_score",
    "abnormality_score",
    "nearest_state_distance",
    "rescue_score",
    "build_audit_record",
    "validate_scenario",
    "detect_direct_leakage",
]
