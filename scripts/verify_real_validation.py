#!/usr/bin/env python3
"""Verify freshly generated empirical outputs; no clinical success gate."""
import argparse
import json
from pathlib import Path
from cardivex.geo_metadata import parse_gse144424_count_column


def verify(directory):
    def read(name):
        return json.loads((directory / name).read_text())
    summary = read('summary.json')
    assert summary['status'] == 'ok' and summary['external_validation_executed'] is True
    assert summary['loso_fold_count'] == 15 and summary['clinical_validation'] is False
    loso = read('GSE144424_loso_temporal_benchmark_v0.4.json')
    assert len(loso['folds']) == 15
    assert len({fold['subject'] for fold in loso['folds']}) == 15
    for fold in loso['folds']:
        fit_subjects = {parse_gse144424_count_column(s).subject_id for s in fold['preprocessing_fit_sample_ids']}
        assert fold['subject'] not in fit_subjects and len(fit_subjects) == 14
    external = read('GSE234907_no_refit_external_validation_v0.5.json')
    assert external['external']['sample_count'] == 6
    assert external['external']['external_fit'] == 'none'
    assert external['direction_transfer'] is None
    for test in external['exact_permutation_tests'].values():
        assert test['permutation_count'] == 20 and test['p_value_two_sided'] >= 0.1
    classifier = read('GSE144424_classification_v0.4.json')
    assert classifier['primary_metrics']['delta_hypoxia_vs_other_accuracy'] >= 0.85
    assert all(result['n_subjects'] == 15 for result in classifier['results'])
    four_class = next(result for result in classifier['results']
                      if result['feature_mode'] == 'delta' and result['label_mode'] == 'four_class')
    queries = [row for row in four_class['predictions'] if row['condition'] != 'normoxia']
    assert len(queries) == 45 and four_class['query_only']['excluded_reference_count'] == 15
    expected = sum(row['true_label'] == row['predicted_label'] for row in queries) / len(queries)
    assert four_class['query_only']['overall_accuracy'] == expected
    bundle = read('next_bundle_summary.json')
    assert bundle['status'] == 'ok' and bundle['frozen_status'] == 'ok'
    full_bundle = read('GSE144424_next_validation_bundle_v0.4.json')
    assert full_bundle['frozen_benchmark']['held_out_group_ids'] == full_bundle['preprocessing_held_out_subjects']
    assert full_bundle['frozen_benchmark']['held_out_subject_count'] == 3
    assert full_bundle['frozen_benchmark']['validation_comparison_count'] == 15
    assert full_bundle['subject_loso_classification']['query_only'] == four_class['query_only']
    assert bundle['atac_matched_pairs'] == 56
    assert bundle['loso_accuracy'] >= 0.55
    print('All fresh empirical output contracts verified; biological and clinical validation remain limited.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    verify(parser.parse_args().directory)
