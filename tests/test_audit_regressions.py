import math

import pytest

from cardivex.external_validation_stats import exact_two_group_permutation
from cardivex.model_evaluation import classification_report
from cardivex.temporal_metrics import trajectory_error
from cardivex.geo_counts import GEOCountMatrix, ModuleScoreConfig, fit_module_scaler, read_geo_counts
from cardivex.calibration import weighted_mean
from cardivex.defense import abnormality_score


@pytest.mark.parametrize('scale', [1e-20, 1.0, 1e20])
def test_exact_permutation_is_invariant_to_units(scale):
    result = exact_two_group_permutation([scale, 2 * scale], [3 * scale, 4 * scale])
    assert result.p_value_two_sided == pytest.approx(1 / 3)


@pytest.mark.parametrize('bad', [math.nan, math.inf, -math.inf])
def test_permutation_rejects_nonfinite(bad):
    with pytest.raises(ValueError):
        exact_two_group_permutation([bad], [1])


def test_exact_permutation_refuses_unbounded_enumeration():
    with pytest.raises(ValueError, match='permutations'):
        exact_two_group_permutation(list(range(20)), list(range(20, 40)))


def test_balanced_accuracy_averages_only_observed_classes():
    report = classification_report(['a', 'new'], ['a', 'a'])
    assert report.balanced_accuracy == 0.5
    assert report.macro_f1 == pytest.approx(1 / 3)


@pytest.mark.parametrize('points', [[(0, 1), (0, 2)], [(math.nan, 1)], [(0, math.inf), (1, 0)]])
def test_trajectory_rejects_ambiguous_or_invalid_points(points):
    with pytest.raises(ValueError):
        trajectory_error({'a': points}, {'a': [(1, 0), (0, 1)]})


@pytest.mark.parametrize('values', ['nan', 'inf', '-1'])
def test_reader_rejects_invalid_counts(tmp_path, values):
    path = tmp_path / 'counts.tsv'
    path.write_text(f'gene\ts1\nG1\t{values}\n')
    with pytest.raises(ValueError):
        read_geo_counts(path)


def test_reader_rejects_version_collisions(tmp_path):
    path = tmp_path / 'counts.tsv'
    path.write_text('gene\ts1\nG1.1\t1\nG1.2\t2\n')
    with pytest.raises(ValueError, match='unique'):
        read_geo_counts(path)


def test_zero_library_cannot_be_scored_as_normal():
    matrix = GEOCountMatrix(('G1',), ('s1',), ((0.0,),))
    with pytest.raises(ValueError, match='positive'):
        fit_module_scaler(matrix, ModuleScoreConfig({'a': ('G1',)}, 1), fit_sample_ids=['s1'])


@pytest.mark.parametrize('weights', [[-1, 2], [math.nan, 1], [math.inf, 1]])
def test_weighted_mean_rejects_invalid_weights(weights):
    with pytest.raises(ValueError):
        weighted_mean([0.1, 0.2], weights)


@pytest.mark.parametrize('weights', [{'a': 0}, {'a': math.nan}, {'a': math.inf}])
def test_abnormality_requires_informative_finite_weights(weights):
    with pytest.raises(ValueError):
        abnormality_score({'a': 0}, {'a': 1}, weights=weights)


def test_missing_domain_is_not_a_zero_measurement():
    from cardivex.calibration import domain_uncertainty, scenario_calibration_error
    for operation in [lambda: abnormality_score({'a': 0}, {'b': 0}),
                      lambda: domain_uncertainty([{'a': 0.2}, {'b': 0.3}]),
                      lambda: scenario_calibration_error({'a': 0.2}, {'b': 0.3})]:
        with pytest.raises(ValueError, match='matching'):
            operation()


def test_single_observation_does_not_claim_zero_uncertainty():
    from cardivex.calibration import uncertainty_band
    band = uncertainty_band([0.7])
    assert (band.lower, band.upper, band.count) == (0, 1, 1)


@pytest.mark.parametrize('bad', [math.nan, math.inf, -1])
def test_state_rejects_invalid_time(bad):
    from cardivex.features import CardiacState
    with pytest.raises(ValueError):
        CardiacState(time=bad)


def test_frozen_transform_rejects_tampering_and_invalid_raw_scores():
    from cardivex.frozen_modules import freeze_module_transform
    from cardivex.geo_counts import ModuleScoreScaler
    artifact = freeze_module_transform(ModuleScoreConfig({'a': ('A',)}, 1),
        ModuleScoreScaler({'a': 1.0}, {'a': 2.0}, ('s1',)),
        dataset_id='study', source_file='counts', source_sha256='abc')
    with pytest.raises(ValueError, match='finite'):
        artifact.apply([{'a': math.nan}])
    artifact.centers['a'] = 2.0
    with pytest.raises(ValueError, match='artifact ID'):
        artifact.apply([{'a': 2.0}])


def test_fold_preprocessing_is_independent_of_held_subject_counts():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('validation_runner', Path(__file__).parents[1] / 'scripts/run_full_validation.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    samples = ('H18499_A', 'H18499_B', 'H18505_A', 'H18505_B')
    config = ModuleScoreConfig({'a': ('G1',)}, 1)
    matrix = GEOCountMatrix(('G1', 'G2'), samples, ((10, 20, 10, 20), (30, 40, 30, 40)))
    perturbed = GEOCountMatrix(('G1', 'G2'), samples, ((10000, 20000, 10, 20), (1, 2, 30, 40)))
    records, first = runner.fold_records(matrix, config, '18499')
    changed, second = runner.fold_records(perturbed, config, '18499')
    assert first == second
    assert first.fit_sample_ids == ('H18505_A', 'H18505_B')
    assert [r.state.domain_scores for r in records[2:]] == [r.state.domain_scores for r in changed[2:]]
    assert records[0].state.domain_scores != changed[0].state.domain_scores


def test_external_reader_does_not_discard_malformed_gene_rows(tmp_path):
    from cardivex.gse234907 import read_gse234907_heart_counts
    path = tmp_path / 'counts.tsv'
    path.write_text('#KEY\ts1\n#CLASS\t2D\n123\tnot-a-count\n')
    with pytest.raises(ValueError, match='non-numeric'):
        read_gse234907_heart_counts(path)


def test_incomparable_modalities_are_explicitly_unavailable():
    from cardivex.features import from_domain_scores
    from cardivex.scoring import score_modalities
    result = score_modalities(from_domain_scores({'a': 0}, imaging={'texture': 0.1}),
                              from_domain_scores({'a': 0}, imaging={'organization': 0.1}))
    assert not result[0].available
    assert result[0].abnormality is None and result[0].novelty is None


def test_serialization_rejects_silent_key_collisions():
    from cardivex.serialization import dumps
    with pytest.raises(ValueError, match='collide'):
        dumps({1: 'one', '1': 'another'})


def test_cli_rejects_invalid_features_before_calling_model(tmp_path):
    from cardivex.cli import run_model
    class Model:
        def predict(self, rows):
            raise AssertionError('must reject before model execution')
    source = tmp_path / 'input.json'
    source.write_text('{"feature_rows": [{"a": NaN}]}')
    destination = tmp_path / 'output.json'
    destination.write_text('previous output')
    with pytest.raises(ValueError, match='finite'):
        run_model(model=Model(), input_path=source, output_path=destination)
    assert destination.read_text() == 'previous output'


def test_frozen_suite_uses_the_preprocessing_holdout_policy(monkeypatch):
    import importlib.util
    from pathlib import Path
    from cardivex.features import from_domain_scores
    from cardivex.ingest import IngestRecord
    scripts = Path(__file__).parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('bundle_runner', scripts / 'run_next_validation_bundle.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    records = []
    subjects = [str(18499 + i) for i in range(12)] + list(runner.HELD_OUT)
    for i, subject in enumerate(subjects):
        for j, time in enumerate((0, 6, 12, 30)):
            state = from_domain_scores({'a': 0.2 + i * 0.01 + j * 0.03}, omics={'rna': 1}, time=time)
            from dataclasses import replace
            state = replace(state, metadata={'subject_id': subject, 'experimental_unit_id': subject})
            records.append(IngestRecord(f'{subject}_{j}', 'GSE144424', 'course', time, state, ('omics',), 'fixture'))
    result = runner.build_frozen_suite(records)
    assert result['status'] == 'ok', result['error']
    assert result['held_out_group_ids'] == sorted(runner.HELD_OUT)
    assert result['development_record_count'] == 48
