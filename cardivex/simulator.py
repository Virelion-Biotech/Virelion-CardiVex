from __future__ import annotations

from typing import Mapping

from .cardiac_state import CardiacLatentState, CardiacObservation, PatientProfile, apply_perturbation, healthy_baseline, observe_state, state_to_domains
from .features import CardiacState, ModalityVector


def simulate_patient(
    patient: PatientProfile,
    perturbation: Mapping[str, float] | None = None,
    *,
    time: float = 0.0,
    seed: int | None = None,
    noise: float = 0.01,
) -> tuple[CardiacLatentState, CardiacObservation, CardiacState]:
    """Run the shared patient → perturbation → phenotype pipeline.

    The returned ``CardiacState`` is directly consumable by the existing
    CardiVex benchmark/evaluation stack.
    """
    latent = apply_perturbation(healthy_baseline(patient), perturbation or {}, time=time)
    observation = observe_state(latent, patient, seed=seed, noise=noise)
    state = CardiacState(
        imaging=ModalityVector("imaging", observation.motion),
        functional=ModalityVector(
            "functional",
            {**observation.ecg, **observation.hemodynamics},
        ),
        omics=ModalityVector("omics", observation.biomarkers),
        domain_scores=state_to_domains(latent),
        time=time,
        metadata={
            "simulator": "shared-cardiac-state-v0",
            "patient_sex": patient.sex,
            "patient_age": str(patient.age),
        },
    )
    return latent, observation, state
