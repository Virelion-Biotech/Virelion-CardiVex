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
    bundle = read('next_bundle_summary.json')
    assert bundle['status'] == 'ok' and bundle['frozen_status'] == 'ok'
    full_bundle = read('GSE144424_next_validation_bundle_v0.4.json')
    assert full_bundle['frozen_benchmark']['held_out_group_ids'] == full_bundle['preprocessing_held_out_subjects']
    assert bundle['atac_matched_pairs'] == 56
    assert bundle['loso_accuracy'] >= 0.55
    print('All fresh empirical output contracts verified; biological and clinical validation remain limited.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    verify(parser.parse_args().directory)
