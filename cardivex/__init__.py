"""CardiVex: computational cardiac challenge and defensive evaluation."""

from .models import Scenario, ScenarioState, EvidenceTier, Confidence
from .engine import generate_variations, interpolate_timeline
from .realism import realism_score
from .defense import abnormality_score, nearest_state_distance, rescue_score
from .audit import build_audit_record
from .validation import validate_scenario, detect_direct_leakage
from .features import CardiacState, ModalityVector, from_domain_scores
from .adapters import imaging_features, functional_features, omics_features, normalize_features
from .physiology import PhysiologicalFeatureConfig, GSE234907Observation, normalize_physiology, ingest_gse234907_physiology
from .gse234907 import GSE234907Matrix, read_gse234907_heart_counts, score_gse234907_modules, class_groups
from .gse234907_frozen import score_gse234907_with_frozen_transform
from .external_validation import ExternalValidationResult, DirectionTransfer, ReferenceSimilarity, validate_external_effect, classify_transferability
from .external_validation_stats import ExactPermutationResult, exact_two_group_permutation, rmse_to_reference
from .frozen_modules import FrozenModuleTransform, compute_artifact_id as compute_frozen_module_artifact_id, freeze_module_transform, frozen_module_transform_json, require_complete_frozen_transform
from .translation import TranslationProfile, default_translation_profile, scenario_to_multimodal
from .attribution import DomainAttribution, attribute_domains
from .benchmark import DetectionResult, RecoveryResult, detect_state, evaluate_recovery
from .pipeline import ChallengeAssessment, EndToEndResult, assess_scenario, run_end_to_end
from .evaluation import CalibrationResult, OODResult, calibration_curve, best_threshold, ood_evaluate, state_abnormality_scores
from .modeling import Prediction, CentroidModel, fit_centroid_model, accuracy
from .model_evaluation import ClassificationReport, classification_report
from .experiments import ModelSpec, FoldResult, CrossValidationResult, cross_validate_centroid, predict_with_model
from .experiment_runner import ExperimentResult, run_centroid_experiment, experiment_json
from .model_registry import ModelRecord, ModelRegistry
from .model_api import ModelPrediction, CardiVexModel, validate_model_predictions
from .temporal_surrogate import TemporalSurrogateSpec, TemporalSurrogate, fit_temporal_surrogate, evaluate_temporal_surrogate
from .temporal_benchmark import TemporalBenchmark, benchmark_temporal_surrogate
from .cardiac_state import PatientProfile, CardiacLatentState, CardiacObservation, generate_patient, healthy_baseline, apply_perturbation, observe_state, state_to_domains
from .simulator import simulate_patient
from .splits import BenchmarkSplit, make_split
from .registry import EvidenceRecord, DatasetRecord, EvidenceRegistry, DatasetRegistry
from .ingest import IngestRecord, ingest_processed_observation, require_modalities
from .loader import records_from_rows, load_csv
from .dataset import DatasetBatch, assemble_batch, split_by_condition
from .quality import QualityIssue, inspect_records, require_clean
from .dataset_qualification import DatasetQualification, qualify_records
from .data_plan import DatasetAnalysisPlan, build_analysis_plan
from .geo_metadata import GEOSampleMetadata, parse_gse144424_sample_title, parse_gse144424_count_column
from .geo_counts import GEOCountMatrix, ModuleScoreConfig, ModuleScoreScaler, read_geo_counts, fit_module_scaler, score_count_modules, parse_gse144424_metadata, parse_gse144424_count_metadata
from .calibration_runner import CalibrationArtifact, ConditionCalibration, build_development_calibration, calibration_json, compute_artifact_id
from .frozen_scenario import build_scenario_from_frozen_calibration
from .frozen_validation import FrozenValidationRun, run_frozen_validation, frozen_validation_json
from .frozen_benchmark import FrozenBenchmark, build_frozen_benchmark, validate_frozen_benchmark_against_groups
from .phenotypes import DomainDistribution, EmpiricalPhenotypeProfile, fit_empirical_profile, profile_distance
from .scenario_builder import ScenarioBuildConfig, build_challenge_scenario, compose_novel_profile
from .trajectory import bounded_trajectory, shift_timeline
from .temporal import TemporalPoint, EmpiricalTemporalProfile, fit_temporal_profile, materialize_trajectory
from .longitudinal import LongitudinalGroup, LongitudinalValidation, group_longitudinal_records, validate_disjoint_longitudinal_groups, validate_longitudinal_group, align_to_time_grid, longitudinal_domain_series, longitudinal_feature_series, collapse_subject_replicates
from .temporal_metrics import TrajectoryError, trajectory_error, temporal_shift_error
from .surrogate_validation import ModalityValidation, SurrogateValidation, validate_scenario_against_group, summarize_surrogate_validation
from .surrogate_runner import SurrogateValidationRun, run_surrogate_validation, surrogate_validation_json
from .validated_benchmark import ValidatedBenchmarkRun, run_validated_benchmark, validated_benchmark_json
from .novelty import normalized_distance, novelty_margin, is_novel
from .correlation import domain_correlation_matrix
from .translation_calibration import TranslationCalibrationResult, fit_translation_profile
from .challenge_families import ChallengeFamily, FAMILIES, build_severity_shift, build_temporal_shift, build_combinatorial, family_is_novel
from .benchmark_factory import BenchmarkManifest, build_manifest, audit_manifest, available_families
from .calibration import CalibrationBand, weighted_mean, uncertainty_band, domain_uncertainty, scenario_calibration_error
from .benchmark_report import BenchmarkSummary, summarize_manifest, compare_scenario_to_observation, summarize_observation_uncertainty
from .suite import BenchmarkRun, ScenarioResult, run_benchmark_suite, build_run_audit, report_summary
from .scoring import ModalityDetectionScore, AssessmentScore, score_modalities, score_assessment, score_recovery
from .serialization import to_jsonable, dumps, write_json

__all__ = [
    "Scenario", "ScenarioState", "EvidenceTier", "Confidence", "generate_variations", "interpolate_timeline", "realism_score",
    "abnormality_score", "nearest_state_distance", "rescue_score", "build_audit_record", "validate_scenario", "detect_direct_leakage",
    "CardiacState", "ModalityVector", "from_domain_scores", "imaging_features", "functional_features", "omics_features", "normalize_features",
    "PhysiologicalFeatureConfig", "GSE234907Observation", "normalize_physiology", "ingest_gse234907_physiology",
    "GSE234907Matrix", "read_gse234907_heart_counts", "score_gse234907_modules", "class_groups", "score_gse234907_with_frozen_transform",
    "ExternalValidationResult", "DirectionTransfer", "ReferenceSimilarity", "validate_external_effect", "classify_transferability",
    "ExactPermutationResult", "exact_two_group_permutation", "rmse_to_reference",
    "FrozenModuleTransform", "compute_frozen_module_artifact_id", "freeze_module_transform", "frozen_module_transform_json", "require_complete_frozen_transform",
    "TranslationProfile", "default_translation_profile", "scenario_to_multimodal", "DomainAttribution", "attribute_domains",
    "DetectionResult", "RecoveryResult", "detect_state", "evaluate_recovery", "ChallengeAssessment", "EndToEndResult",
    "assess_scenario", "run_end_to_end", "CalibrationResult", "OODResult", "calibration_curve", "best_threshold", "ood_evaluate", "state_abnormality_scores",
    "Prediction", "CentroidModel", "fit_centroid_model", "accuracy", "ClassificationReport", "classification_report",
    "ModelSpec", "FoldResult", "CrossValidationResult", "cross_validate_centroid", "predict_with_model", "ModelRecord", "ModelRegistry",
    "ModelPrediction", "CardiVexModel", "validate_model_predictions",
    "TemporalSurrogateSpec", "TemporalSurrogate", "fit_temporal_surrogate", "evaluate_temporal_surrogate", "TemporalBenchmark", "benchmark_temporal_surrogate",
    "PatientProfile", "CardiacLatentState", "CardiacObservation", "generate_patient", "healthy_baseline", "apply_perturbation", "observe_state", "state_to_domains", "simulate_patient",
    "ExperimentResult", "run_centroid_experiment", "experiment_json", "BenchmarkSplit", "make_split",
    "EvidenceRecord", "DatasetRecord", "EvidenceRegistry", "DatasetRegistry", "IngestRecord", "ingest_processed_observation", "require_modalities",
    "records_from_rows", "load_csv", "DatasetBatch", "assemble_batch", "split_by_condition", "QualityIssue", "inspect_records", "require_clean",
    "DatasetQualification", "qualify_records", "DatasetAnalysisPlan", "build_analysis_plan",
    "GEOSampleMetadata", "parse_gse144424_sample_title", "parse_gse144424_count_column", "GEOCountMatrix", "ModuleScoreConfig", "ModuleScoreScaler", "read_geo_counts", "fit_module_scaler", "score_count_modules", "parse_gse144424_metadata", "parse_gse144424_count_metadata",
    "CalibrationArtifact", "ConditionCalibration", "build_development_calibration", "calibration_json", "compute_artifact_id",
    "build_scenario_from_frozen_calibration", "FrozenValidationRun", "run_frozen_validation", "frozen_validation_json",
    "FrozenBenchmark", "build_frozen_benchmark", "validate_frozen_benchmark_against_groups",
    "DomainDistribution", "EmpiricalPhenotypeProfile", "fit_empirical_profile", "profile_distance", "ScenarioBuildConfig", "build_challenge_scenario", "compose_novel_profile",
    "bounded_trajectory", "shift_timeline", "TemporalPoint", "EmpiricalTemporalProfile", "fit_temporal_profile", "materialize_trajectory",
    "LongitudinalGroup", "LongitudinalValidation", "group_longitudinal_records", "validate_disjoint_longitudinal_groups", "validate_longitudinal_group", "align_to_time_grid", "longitudinal_domain_series", "longitudinal_feature_series", "collapse_subject_replicates",
    "TrajectoryError", "trajectory_error", "temporal_shift_error", "ModalityValidation", "SurrogateValidation", "validate_scenario_against_group", "summarize_surrogate_validation",
    "SurrogateValidationRun", "run_surrogate_validation", "surrogate_validation_json", "ValidatedBenchmarkRun", "run_validated_benchmark", "validated_benchmark_json",
    "normalized_distance", "novelty_margin", "is_novel", "domain_correlation_matrix", "TranslationCalibrationResult", "fit_translation_profile",
    "ChallengeFamily", "FAMILIES", "build_severity_shift", "build_temporal_shift", "build_combinatorial", "family_is_novel",
    "BenchmarkManifest", "build_manifest", "audit_manifest", "available_families",
    "CalibrationBand", "weighted_mean", "uncertainty_band", "domain_uncertainty", "scenario_calibration_error",
    "BenchmarkSummary", "summarize_manifest", "compare_scenario_to_observation", "summarize_observation_uncertainty",
    "BenchmarkRun", "ScenarioResult", "run_benchmark_suite", "build_run_audit", "report_summary",
    "ModalityDetectionScore", "AssessmentScore", "score_modalities", "score_assessment", "score_recovery",
    "to_jsonable", "dumps", "write_json",
]
