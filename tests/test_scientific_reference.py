"""Optional independent CPU references; required in the reference CI job."""
import warnings

import pytest

np = pytest.importorskip('numpy')
scipy = pytest.importorskip('scipy.stats')
sklearn = pytest.importorskip('sklearn.metrics')

from cardivex.external_validation_stats import exact_two_group_permutation
from cardivex.model_evaluation import classification_report


@pytest.mark.parametrize('seed', range(10))
def test_exact_two_sided_matches_scipy(seed):
    rng = np.random.default_rng(seed)
    a, b = rng.normal(size=3), rng.normal(size=3)
    ours = exact_two_group_permutation(a, b)
    reference = scipy.permutation_test((a, b), lambda x, y: np.mean(y) - np.mean(x),
                                      n_resamples=np.inf, alternative='two-sided')
    assert ours.p_value_two_sided == pytest.approx(reference.pvalue)


@pytest.mark.parametrize('predicted,observed', [(['a', 'new'], ['a', 'a']),
    (['a', 'a', 'b', 'b'], ['a', 'b', 'b', 'c']), (['a', 'b'], ['a', 'b'])])
def test_classification_matches_sklearn(predicted, observed):
    report = classification_report(predicted, observed)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        balanced = sklearn.balanced_accuracy_score(observed, predicted)
    assert report.balanced_accuracy == pytest.approx(balanced)
    assert report.accuracy == pytest.approx(sklearn.accuracy_score(observed, predicted))
    assert report.macro_f1 == pytest.approx(sklearn.f1_score(observed, predicted, average='macro', zero_division=0))
