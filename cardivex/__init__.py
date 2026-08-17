"""CardiVex: computational cardiac challenge and defensive evaluation."""

from .models import Scenario, ScenarioState, EvidenceTier, Confidence
from .engine import generate_variations, interpolate_timeline
from .realism import realism_score
from .defense import abnormality_score, nearest_state_distance, rescue_score
from .audit import build_audit_record
from .validation import validate_scenario, detect_direct_leakage
from .features import CardiacState, ModalityVector, from_domain_scores
from .adapters import imaging_features, functional_features, omics_features, normalize_features
from .translation import TranslationProfile, default_translation_profile, scenario_to_multimodal
from .attribution import DomainAttribution, attribute_domains
from .benchmark import DetectionResult, RecoveryResult, detect_state, evaluate_recovery
from .pipeline import ChallengeAssessment, EndToEndResult, assess_scenario, run_end_to_end
from .evaluation import CalibrationResult, OODResult, calibration_curve, best_threshold, ood_evaluate, state_abnormality_scores
from .modeling import Prediction, CentroidModel, fit_centroid_model, accuracy
from .splits import BenchmarkSplit, make_split
from .registry import EvidenceRecord, DatasetRecord, EvidenceRegistry, DatasetRegistry
from .ingest import IngestRecord, ingest_processed_observation, require_modalities

__all__ = [
    "Scenario", "ScenarioState", "EvidenceTier", "Confidence",
    "generate_variations", "interpolate_timeline", "realism_score",
    "abnormality_score", "nearest_state_distance", "rescue_score",
    "build_audit_record", "validate_scenario", "detect_direct_leakage",
    "CardiacState", "ModalityVector", "from_domain_scores",
    "imaging_features", "functional_features", "omics_features", "normalize_features",
    "TranslationProfile", "default_translation_profile", "scenario_to_multimodal",
    "DomainAttribution", "attribute_domains", "DetectionResult", "RecoveryResult",
    "detect_state", "evaluate_recovery", "ChallengeAssessment", "EndToEndResult",
    "assess_scenario", "run_end_to_end", "CalibrationResult", "OODResult",
    "calibration_curve", "best_threshold", "ood_evaluate", "state_abnormality_scores",
    "Prediction", "CentroidModel", "fit_centroid_model", "accuracy",
    "BenchmarkSplit", "make_split",
    "EvidenceRecord", "DatasetRecord", "EvidenceRegistry", "DatasetRegistry",
    "IngestRecord", "ingest_processed_observation", "require_modalities",
]
