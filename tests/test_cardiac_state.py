from cardivex.cardiac_state import (
    CardiacLatentState,
    apply_perturbation,
    generate_patient,
    healthy_baseline,
    observe_state,
    state_to_domains,
)


def test_patient_generation_is_reproducible_and_correlated():
    first = generate_patient(42)
    second = generate_patient(42)
    assert first == second
    assert first.bsa > 0
    assert first.systolic_bp > first.diastolic_bp


def test_shared_state_supports_multiple_mechanisms():
    patient = generate_patient(7)
    baseline = healthy_baseline(patient)
    ischemic = apply_perturbation(baseline, {"ischemia": 0.8}, time=2.0)
    mixed = apply_perturbation(
        baseline,
        {
            "ischemia": 0.8,
            "inflammation": 0.5,
            "metabolic": 0.4,
        },
        time=2.0,
    )
    assert ischemic.ischemic_burden > baseline.ischemic_burden
    assert mixed.inflammatory_activation > ischemic.inflammatory_activation
    assert mixed.metabolic_stress > baseline.metabolic_stress
    assert mixed.contractility >= ischemic.contractility


def test_observation_layer_is_bounded_and_multimodal():
    patient = generate_patient(11)
    state = apply_perturbation(healthy_baseline(patient), {"electrophysiology": 0.7, "injury": 0.3})
    observation = observe_state(state, patient, seed=99, noise=0.0)
    for modality in (observation.ecg, observation.hemodynamics, observation.motion, observation.biomarkers):
        assert modality
        assert all(0.0 <= value <= 1.0 for value in modality.values())
    domains = state_to_domains(state)
    assert set(domains) == {
        "electrophysiologic_disturbance",
        "contractile_impairment",
        "endothelial_vascular_dysfunction",
        "metabolic_stress",
        "inflammatory_activation",
        "structural_disorganization",
        "viability_burden",
        "oxidative_stress",
        "mitochondrial_dysfunction",
        "fibrosis_remodeling",
    }
    assert all(0.0 <= value <= 1.0 for value in domains.values())


def test_zero_perturbation_preserves_baseline_state():
    patient = generate_patient(3)
    baseline = healthy_baseline(patient)
    assert apply_perturbation(baseline, {}, time=0.0) == baseline
