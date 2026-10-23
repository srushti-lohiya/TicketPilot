"""Report parsing and provenance tests. No inference, training, network, or application DB writes."""
import json
from pathlib import Path
import pytest
from src.evaluation_snapshot import (
    ROOT, DEFAULT_OUTPUT, build_snapshot, canonical, metric, parse_classifier,
    parse_e2e, parse_per_intent, parse_predictions, parse_retrieval, confusion,
)


def test_snapshot_matches_real_artifacts_and_sample_scopes():
    s = build_snapshot()
    assert canonical(s) == canonical(json.loads(DEFAULT_OUTPUT.read_text()))
    c = s['classifier']['data']
    raw = json.loads((ROOT / 'reports/classifier_report.json').read_text())
    assert c['bitextAccuracy'] == raw['bitext_test']['accuracy']
    assert c['bitextF1'] == raw['bitext_test']['macro_f1']
    assert c['baselineAccuracy'] == raw['bitext_test']['baseline_accuracy']
    assert c['bitextN'] == 3642
    assert (c['realisticN'], c['realisticInScopeN'], c['realisticOosN']) == (33, 27, 6)
    assert c['realisticF1'] is None  # Never confuse the full pipeline CSV with the classifier test split.
    assert len(s['perIntent']['data']) == 27
    assert len(s['retrieval']['data']) == 8
    assert not any('rerank' in r['mode'] for r in s['retrieval']['data'])
    assert all(len(source['sha256']) == 64 for source in s['sources'])
    assert 'text' not in s['confusion']['data']  # No raw ticket corpus embedded in the snapshot.


def test_confusion_and_safety_denominators_come_from_recorded_predictions():
    s = build_snapshot()
    cm = s['confusion']['data']
    assert sum(map(sum, cm['matrix'])) == cm['n'] == 54
    assert sum(cm['matrix'][i][i] for i in range(len(cm['labels']))) == cm['correct'] == 37
    assert 'out_of_scope' not in cm['labels']
    assert sum(r['count'] for r in cm['topConfusions']) == 17
    counts = s['e2e']['data']['counts']
    assert counts['guardrailPassed'] == 56 and counts['drafted'] == 59
    assert counts['groundedPassed'] == 35 and counts['groundedEligible'] == 51
    assert counts['autoCorrect'] == 10 and counts['autoResolved'] == 10
    assert counts['oosHeld'] == counts['oos'] == 12
    assert counts['routing'] == {'needs_review': 49, 'auto_resolved': 10, 'escalated': 7}


@pytest.mark.parametrize('value', [True, False, '0.9', -0.1, 1.1, float('nan'), float('inf'), None])
def test_invalid_rate_is_not_measured(value):
    assert metric({'a': value}, 'a', rate=True) is None


def test_zero_is_a_real_measurement_and_missing_fields_stay_null():
    c = parse_classifier({'bitext_test': {'accuracy': 0}, 'auto_threshold': 0})
    assert c['bitextAccuracy'] == 0 and c['threshold'] == 0
    assert c['bitextF1'] is None and c['realisticAccuracy'] is None
    assert c['bitextN'] is None and c['realisticInScopeN'] is None
    e = parse_e2e({'avg_tokens_per_ticket': 0, 'auto_resolve_precision': None})
    assert e['avgTokens'] == 0 and e['autoPrecision'] is None
    assert e['p50'] is None and e['counts'] is None


def test_missing_sources_are_independent_not_a_whole_page_failure(tmp_path):
    folder = tmp_path / 'reports'
    folder.mkdir()
    (folder / 'classifier_report.json').write_text('{"bitext_test":{"accuracy":0.75}}')
    (folder / 'e2e_fallback.json').write_text('invalid json')
    s = build_snapshot(root=tmp_path)
    assert s['classifier']['data']['bitextAccuracy'] == 0.75
    assert s['classifier']['data']['bitextN'] is None
    assert s['e2e']['data'] is None and 'Not measured' in s['e2e']['error']
    assert s['retrieval']['data'] is None
    assert s['confusion']['data'] is None
    assert s['modelArtifactSha256AtGeneration'] is None
    json.dumps(s, allow_nan=False)


def test_csv_missing_values_stay_unmeasured_without_invented_configurations():
    rows = parse_retrieval('set,mode,recall@3,mrr,n\nrealistic,bm25,,0,54\n')
    assert rows == [{'set': 'realistic', 'mode': 'bm25', 'recall': None, 'mrr': 0.0, 'n': 54}]
    with pytest.raises(ValueError):
        parse_retrieval('bad,header\n')
    with pytest.raises(ValueError):
        parse_retrieval('set,mode,recall@3,mrr,n\na,b,0,0,1\na,b,1,1,1\n')


def test_incomplete_per_intent_report_cannot_claim_full_support():
    text = 'track_order 1.0 1.0 1.0 12\naccuracy 0.99 100\n'
    rows = parse_per_intent(text)
    assert rows[0]['support'] == 12
    assert parse_classifier({}, rows, per_intent_text=text)['bitextN'] is None


def test_classifier_split_counts_require_matching_recorded_total():
    dataset = [{'intent': 'track_order', 'split': 'test'}]
    assert parse_classifier({'realistic_test': {'n': 33}}, dataset=dataset)['realisticInScopeN'] is None
    assert parse_classifier({'realistic_test': {'n': 1}}, dataset=dataset)['realisticInScopeN'] == 1


def test_invalid_predictions_never_generate_a_confusion_matrix():
    with pytest.raises(ValueError):
        parse_predictions('true,pred,status,oos,guard_ok,has_reply,grounded,intent_ok\na,a,needs_review,False,True,True,True,False\n')
    assert confusion([]) is None


def test_mismatched_pipeline_summary_does_not_borrow_denominators():
    predictions = parse_predictions((ROOT / 'reports/e2e_fallback.csv').read_text())
    assert parse_e2e({'tickets': 1}, predictions)['counts'] is None
