from cardivex.benchmark_factory import audit_manifest, build_manifest
from cardivex.challenge_families import build_severity_shift
from cardivex.ingest import ingest_processed_observation
from cardivex.phenotypes import fit_empirical_profile
from cardivex.scenario_builder import build_challenge_scenario


def _profile():
    records = [
        ingest_processed_observation(
            observation_id=f"obs-{i}",
            dataset_id="DS-TEST",
            condition="challenge_proxy",
            time=float(i),
            domain_scores={"inflammatory_activation": 0.3 + 0.05 * i, "contractile_impairment": 0.2 + 0.04 * i},
        )
        for i in range(1, 7)
    ]
    return fit_empirical_profile(records, condition="challenge_proxy")


def test_manifest_sorts_and_validates():
    scenario = build_challenge_scenario(
        _profile(),
        scenario_id="CVX-7002",
        name="test",
        target_model="human_iPSC_derived_cardiac_tissue",
    )
    manifest = build_manifest([scenario])
    assert manifest.ids() == ("CVX-7002",)


def test_severity_family_is_held_out():
    scenario = build_severity_shift(_profile(), scenario_id="CVX-7003", scale=1.2)
    assert scenario.ood_status == "held_out_novel"


def test_manifest_audit_detects_exact_training_leakage():
    profile = _profile()
    train = [build_challenge_scenario(profile, scenario_id="CVX-7004", name="train", target_model="human_iPSC_derived_cardiac_tissue")]
    held_out = [train[0]]
    audit = audit_manifest(train, held_out)
    assert not audit["clean"]
    assert "SCENARIO_ID_LEAK" in audit["leakage_issues"]
