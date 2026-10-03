from __future__ import annotations

from dataclasses import dataclass, replace
from math import exp, sqrt
from random import Random
from typing import Mapping


@dataclass(frozen=True)
class PatientProfile:
    """Patient-level covariates used to construct a normalized baseline state."""

    age: float
    sex: str
    bsa: float
    heart_rate: float
    systolic_bp: float
    diastolic_bp: float

    def __post_init__(self) -> None:
        if not 18.0 <= self.age <= 100.0:
            raise ValueError("age must be between 18 and 100 years")
        if self.sex not in {"female", "male"}:
            raise ValueError("sex must be 'female' or 'male'")
        if self.bsa <= 0 or self.heart_rate <= 0 or self.systolic_bp <= self.diastolic_bp:
            raise ValueError("BSA, heart rate, and blood pressure must be physiologically ordered")


@dataclass(frozen=True)
class CardiacLatentState:
    """Compact, normalized latent cardiac state.

    Values are deliberately dimensionless and bounded. This is a computational
    phenotype representation, not a mechanistic clinical simulator.
    """

    contractility: float
    electrical_instability: float
    vascular_dysfunction: float
    metabolic_stress: float
    inflammatory_activation: float
    structural_remodeling: float
    tissue_injury: float
    ischemic_burden: float = 0.0
    time: float = 0.0

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if name == "time":
                continue
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.time < 0:
            raise ValueError("time must be non-negative")


@dataclass(frozen=True)
class CardiacObservation:
    """Observable cardiac outputs derived from a latent state."""

    ecg: Mapping[str, float]
    hemodynamics: Mapping[str, float]
    motion: Mapping[str, float]
    biomarkers: Mapping[str, float]


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normal(rng: Random, sd: float) -> float:
    return rng.gauss(0.0, sd) if sd else 0.0


def generate_patient(seed: int | None = None) -> PatientProfile:
    """Generate a reproducible healthy patient with correlated covariates."""
    rng = Random(seed)
    age = rng.uniform(20.0, 80.0)
    sex = "female" if rng.random() < 0.5 else "male"
    bsa = _clip(rng.gauss(1.85 if sex == "male" else 1.68, 0.16)) * 2.0
    # Heart rate, pressure and body size are generated conditionally rather than independently.
    heart_rate = max(52.0, min(92.0, 74.0 - 0.10 * (age - 45.0) + _normal(rng, 6.0)))
    systolic = max(95.0, min(155.0, 112.0 + 0.30 * (age - 45.0) + _normal(rng, 9.0)))
    diastolic = max(55.0, min(systolic - 15.0, 72.0 + 0.12 * (age - 45.0) + _normal(rng, 5.0)))
    return PatientProfile(age, sex, bsa, heart_rate, systolic, diastolic)


def healthy_baseline(patient: PatientProfile) -> CardiacLatentState:
    """Construct a healthy latent state with mild age-dependent variation."""
    age_factor = _clip((patient.age - 20.0) / 80.0)
    return CardiacLatentState(
        contractility=_clip(0.18 + 0.08 * age_factor),
        electrical_instability=_clip(0.08 + 0.08 * age_factor),
        vascular_dysfunction=_clip(0.08 + 0.18 * age_factor),
        metabolic_stress=_clip(0.07 + 0.10 * age_factor),
        inflammatory_activation=_clip(0.05 + 0.08 * age_factor),
        structural_remodeling=_clip(0.04 + 0.10 * age_factor),
        tissue_injury=0.02,
    )


def apply_perturbation(
    baseline: CardiacLatentState,
    perturbation: Mapping[str, float],
    *,
    time: float = 0.0,
) -> CardiacLatentState:
    """Apply normalized host-response perturbations to the shared state space.

    Keys represent mechanism-level burdens (for example ``ischemia`` or
    ``inflammation``), not agents, procedures, or experimental instructions.
    Multiple perturbations interact through shared latent physiology.
    """
    p = {str(k): _clip(v) for k, v in perturbation.items()}
    ischemia = p.get("ischemia", 0.0)
    inflammation = p.get("inflammation", 0.0)
    electrophysiology = p.get("electrophysiology", 0.0)
    injury = p.get("injury", 0.0)
    pathogen_host_response = p.get("pathogen_host_response", 0.0)
    metabolic = p.get("metabolic", 0.0)
    genetic_susceptibility = p.get("genetic_susceptibility", 0.0)

    host_inflammation = _clip(inflammation + 0.75 * pathogen_host_response)
    injury_burden = _clip(injury + 0.45 * ischemia + 0.35 * metabolic)
    electrical = _clip(
        baseline.electrical_instability
        + 0.70 * electrophysiology
        + 0.30 * ischemia
        + 0.20 * injury
        + 0.20 * genetic_susceptibility
    )
    vascular = _clip(
        baseline.vascular_dysfunction
        + 0.65 * ischemia
        + 0.55 * host_inflammation
        + 0.25 * metabolic
    )
    contractility = _clip(
        baseline.contractility
        + 0.70 * ischemia
        + 0.45 * injury_burden
        + 0.30 * metabolic
        + 0.20 * genetic_susceptibility
        + 0.15 * host_inflammation
    )
    remodeling = _clip(
        baseline.structural_remodeling
        + 0.35 * injury_burden
        + 0.30 * host_inflammation
        + 0.25 * genetic_susceptibility
    )
    return replace(
        baseline,
        contractility=contractility,
        electrical_instability=electrical,
        vascular_dysfunction=vascular,
        metabolic_stress=_clip(baseline.metabolic_stress + 0.65 * metabolic + 0.25 * injury_burden),
        inflammatory_activation=_clip(baseline.inflammatory_activation + host_inflammation),
        structural_remodeling=remodeling,
        # Preserve baseline residual injury when no injury-related mechanism is applied.
        tissue_injury=_clip(baseline.tissue_injury + injury + 0.45 * ischemia + 0.35 * metabolic),
        ischemic_burden=_clip(baseline.ischemic_burden + ischemia),
        time=time,
    )


def observe_state(
    state: CardiacLatentState,
    patient: PatientProfile,
    *,
    seed: int | None = None,
    noise: float = 0.01,
) -> CardiacObservation:
    """Map latent physiology to normalized observable proxies with measurement noise."""
    if noise < 0:
        raise ValueError("noise must be non-negative")
    rng = Random(seed)
    baseline_edv = 120.0 * (patient.bsa / 1.8)
    volume_penalty = 0.35 * state.structural_remodeling
    contractility_loss = 0.45 * state.contractility
    esv = baseline_edv * _clip(0.42 + contractility_loss + volume_penalty)
    edv = baseline_edv * (1.0 + 0.12 * state.structural_remodeling)
    sv = max(1.0, edv - esv)
    ef = _clip(sv / edv)
    hr = patient.heart_rate * (1.0 + 0.12 * state.inflammatory_activation + 0.05 * state.metabolic_stress)
    co = hr * sv / 1000.0
    afterload = patient.systolic_bp / 120.0

    ecg = {
        "heart_rate": _clip(hr / 160.0 + _normal(rng, noise)),
        "qrs_duration": _clip(0.25 + 0.28 * state.electrical_instability + _normal(rng, noise)),
        "repolarization_abnormality": _clip(0.15 + 0.55 * state.electrical_instability + 0.18 * state.ischemic_burden + _normal(rng, noise)),
        "st_t_abnormality": _clip(0.10 + 0.68 * state.ischemic_burden + 0.22 * state.inflammatory_activation + _normal(rng, noise)),
    }
    hemodynamics = {
        "edv": _clip(edv / 220.0 + _normal(rng, noise)),
        "esv": _clip(esv / 180.0 + _normal(rng, noise)),
        "ejection_fraction": _clip(ef + _normal(rng, noise)),
        "stroke_volume": _clip(sv / 130.0 + _normal(rng, noise)),
        "cardiac_output": _clip(co / 10.0 + _normal(rng, noise)),
        "afterload": _clip(afterload / 2.0 + 0.12 * state.vascular_dysfunction + _normal(rng, noise)),
    }
    motion = {
        "global_wall_motion_impairment": _clip(0.10 + 0.65 * state.contractility + 0.20 * state.tissue_injury + _normal(rng, noise)),
        "regional_motion_heterogeneity": _clip(0.08 + 0.70 * state.ischemic_burden + 0.18 * state.structural_remodeling + _normal(rng, noise)),
    }
    biomarkers = {
        "injury_marker": _clip(0.03 + 0.78 * state.tissue_injury + _normal(rng, noise)),
        "inflammation_marker": _clip(0.04 + 0.72 * state.inflammatory_activation + _normal(rng, noise)),
        "stress_marker": _clip(0.05 + 0.55 * state.metabolic_stress + 0.20 * state.contractility + _normal(rng, noise)),
    }
    return CardiacObservation(ecg, hemodynamics, motion, biomarkers)


def state_to_domains(state: CardiacLatentState) -> dict[str, float]:
    """Convert the latent state into CardiVex's existing normalized domains."""
    return {
        "electrophysiologic_disturbance": state.electrical_instability,
        "contractile_impairment": state.contractility,
        "endothelial_vascular_dysfunction": state.vascular_dysfunction,
        "metabolic_stress": state.metabolic_stress,
        "inflammatory_activation": state.inflammatory_activation,
        "structural_disorganization": state.structural_remodeling,
        "viability_burden": state.tissue_injury,
        "oxidative_stress": _clip(0.55 * state.metabolic_stress + 0.35 * state.tissue_injury),
        "mitochondrial_dysfunction": _clip(0.65 * state.metabolic_stress + 0.25 * state.tissue_injury),
        "fibrosis_remodeling": state.structural_remodeling,
    }
